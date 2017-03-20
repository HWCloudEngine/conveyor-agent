# Copyright (c) 2012 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Volume-related Utilities and helpers."""


import math

from oslo_config import cfg

from conveyoragent.brick import units
from conveyoragent.common import log as logging
from conveyoragent.common import processutils
from conveyoragent.common import strutils
from conveyoragent.common import timeutils
from conveyoragent import exception
from conveyoragent.i18n import _
from conveyoragent import utils


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def null_safe_str(s):
    return str(s) if s else ''


def setup_blkio_cgroup(srcpath, dstpath, bps_limit, execute=utils.execute):
    if not bps_limit:
        LOG.debug('Not using bps rate limiting on volume copy')
        return None

    try:
        srcdev = utils.get_blkdev_major_minor(srcpath)
    except exception.Error as e:
        msg = (_('Failed to get device number for read throttling: %(error)s')
               % {'error': e})
        LOG.error(msg)
        srcdev = None

    try:
        dstdev = utils.get_blkdev_major_minor(dstpath)
    except exception.Error as e:
        msg = (_('Failed to get device number for write throttling: %(error)s')
               % {'error': e})
        LOG.error(msg)
        dstdev = None

    if not srcdev and not dstdev:
        return None

    group_name = CONF.volume_copy_blkio_cgroup_name
    LOG.debug('Setting rate limit to %s bps for blkio '
              'group: %s' % (bps_limit, group_name))
    try:
        execute('cgcreate', '-g', 'blkio:%s' % group_name, run_as_root=True)
    except processutils.ProcessExecutionError:
        LOG.warn(_('Failed to create blkio cgroup'))
        return None

    try:
        if srcdev:
            execute('cgset', '-r', 'blkio.throttle.read_bps_device=%s %d'
                    % (srcdev, bps_limit), group_name, run_as_root=True)
        if dstdev:
            execute('cgset', '-r', 'blkio.throttle.write_bps_device=%s %d'
                    % (dstdev, bps_limit), group_name, run_as_root=True)
    except processutils.ProcessExecutionError:
        msg = (_('Failed to setup blkio cgroup to throttle the devices: '
                 '\'%(src)s\',\'%(dst)s\'')
               % {'src': srcdev, 'dst': dstdev})
        LOG.warn(msg)
        return None

    return ['cgexec', '-g', 'blkio:%s' % group_name]


def _calculate_count(size_in_m, blocksize):

    # Check if volume_dd_blocksize is valid
    try:
        # Rule out zero-sized/negative/float dd blocksize which
        # cannot be caught by strutils
        if blocksize.startswith(('-', '0')) or '.' in blocksize:
            raise ValueError
        bs = strutils.string_to_bytes('%sB' % blocksize)
    except ValueError:
        msg = (_("Incorrect value error: %(blocksize)s, "
                 "it may indicate that \'volume_dd_blocksize\' "
                 "was configured incorrectly. Fall back to default.")
               % {'blocksize': blocksize})
        LOG.warn(msg)
        # Fall back to default blocksize
        CONF.clear_override('volume_dd_blocksize')
        blocksize = CONF.volume_dd_blocksize
        bs = strutils.string_to_bytes('%sB' % blocksize)

    count = math.ceil(size_in_m * units.Mi / bs)

    return blocksize, int(count)


def check_for_odirect_support(src, dest, flag='oflag=direct'):

    # Check whether O_DIRECT is supported
    try:
        utils.execute('dd', 'count=0', 'if=%s' % src, 'of=%s' % dest,
                      flag, run_as_root=True)
        return True
    except processutils.ProcessExecutionError:
        return False


def copy_volume(srcstr, deststr, size_in_m, blocksize, sync=False,
                execute=utils.execute, ionice=None):
    # Use O_DIRECT to avoid thrashing the system buffer cache
    extra_flags = []
    if check_for_odirect_support(srcstr, deststr, 'iflag=direct'):
        extra_flags.append('iflag=direct')

    if check_for_odirect_support(srcstr, deststr, 'oflag=direct'):
        extra_flags.append('oflag=direct')

    # If the volume is being unprovisioned then
    # request the data is persisted before returning,
    # so that it's not discarded from the cache.
    if sync and not extra_flags:
        extra_flags.append('conv=fdatasync')

    blocksize, count = _calculate_count(size_in_m, blocksize)

    cmd = ['dd', 'if=%s' % srcstr, 'of=%s' % deststr,
           'count=%d' % count, 'bs=%s' % blocksize]
    cmd.extend(extra_flags)

    if ionice is not None:
        cmd = ['ionice', ionice] + cmd

    cgcmd = setup_blkio_cgroup(srcstr, deststr, CONF.volume_copy_bps_limit)
    if cgcmd:
        cmd = cgcmd + cmd

    # Perform the copy
    start_time = timeutils.utcnow()
    execute(*cmd, run_as_root=True)
    duration = timeutils.delta_seconds(start_time, timeutils.utcnow())

    # NOTE(jdg): use a default of 1, mostly for unit test, but in
    # some incredible event this is 0 (cirros image?) don't barf
    if duration < 1:
        duration = 1
    mbps = (size_in_m / duration)
    mesg = ("Volume copy details: src %(src)s, dest %(dest)s, "
            "size %(sz).2f MB, duration %(duration).2f sec")
    LOG.debug(mesg % {"src": srcstr,
                      "dest": deststr,
                      "sz": size_in_m,
                      "duration": duration})
    mesg = _("Volume copy %(size_in_m).2f MB at %(mbps).2f MB/s")
    LOG.info(mesg % {'size_in_m': size_in_m, 'mbps': mbps})


def clear_volume(volume_size, volume_path, volume_clear=None,
                 volume_clear_size=None, volume_clear_ionice=None):
    """Unprovision old volumes to prevent data leaking between users."""
    if volume_clear is None:
        volume_clear = CONF.volume_clear

    if volume_clear_size is None:
        volume_clear_size = CONF.volume_clear_size

    if volume_clear_size == 0:
        volume_clear_size = volume_size

    if volume_clear_ionice is None:
        volume_clear_ionice = CONF.volume_clear_ionice

    LOG.info(_("Performing secure delete on volume: %s") % volume_path)

    if volume_clear == 'zero':
        return copy_volume('/dev/zero', volume_path, volume_clear_size,
                           CONF.volume_dd_blocksize,
                           sync=True, execute=utils.execute,
                           ionice=volume_clear_ionice)
    elif volume_clear == 'shred':
        clear_cmd = ['shred', '-n3']
        if volume_clear_size:
            clear_cmd.append('-s%dMiB' % volume_clear_size)
    else:
        raise exception.InvalidConfigurationValue(
            option='volume_clear',
            value=volume_clear)

    clear_cmd.append(volume_path)
    start_time = timeutils.utcnow()
    utils.execute(*clear_cmd, run_as_root=True)
    duration = timeutils.delta_seconds(start_time, timeutils.utcnow())

    # NOTE(jdg): use a default of 1, mostly for unit test, but in
    # some incredible event this is 0 (cirros image?) don't barf
    if duration < 1:
        duration = 1
    LOG.info(_('Elapsed time for clear volume: %.2f sec') % duration)
