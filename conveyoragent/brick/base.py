# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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
"""
Helper code for the iSCSI volume driver.

"""

from oslo_concurrency import processutils as putils
from oslo_config import cfg
from oslo_log import log as logging

from conveyoragent.brick import exception
from conveyoragent.brick import executor

disk_data_opts = [
    cfg.IntOpt('ibs',
               default=1000,
               help='read data from disk each time, unit is '),
    cfg.IntOpt('obs ',
               default=1000,
               help='write data from disk each time, unit is '),
]

CONF = cfg.CONF
CONF.register_opts(disk_data_opts)

LOG = logging.getLogger(__name__)


class BaseCmd(executor.Executor):
    """shell  cmds administration.

    Base class for shell  cmds.
    """

    def __init__(self, root_helper, execute):
        super(BaseCmd, self).__init__(root_helper, execute=execute)

    def _run(self, *args, **kwargs):
        self._execute(*args, run_as_root=True, **kwargs)


class MigrationCmd(BaseCmd):

    def __init__(self, root_helper, execute=putils.execute):
        super(MigrationCmd, self).__init__(root_helper, execute)

    def check_disk_exist(self, disk_name):
        (out, err) = self._execute('ls', disk_name, run_as_root=True)

        if out == disk_name:
            return True
        else:
            return False

    def get_disk_format(self, disk_name):
        # '/\/dev\/vdb/ {print $7}'
        # (out, err) = self._execute('df', '-T', '|', 'awk', '\''+ '$1==' +
        #  '"' + disk_name + '"' +' {print $2}\'', run_as_root=True)
        # (out, err) = self._execute('df ' + '-T' + ' |' + ' grep '
        #   + disk_name, run_as_root=True)
        try:
            dev_names = disk_name.lstrip().split('/')
            if len(dev_names) > 1:
                dev_name = dev_names[-1]
            else:
                dev_name = disk_name

            disk_format = None
            (out, err) = self._execute('lsblk', '-lf', run_as_root=True)

            lines = out.split('\n')

            for line in lines:
                if dev_name in line:
                    values = [l for l in line.split(" ") if l != '']
                    LOG.error("line: %s", values)
                    if len(values) < 2:
                        return None
                    disk_format = values[1]
                    break
            return disk_format

        except putils.ProcessExecutionError as e:

            LOG.error("query disk format cmd error: disk name is"
                      " %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None

    def get_disk_mount_point(self, disk_name):
        '''query disk mount point.'''
        try:
            mount_point = None
            # TODO(t) multi partition must add later
            (out, err) = self._execute('df', '-T', run_as_root=True)

            lines = out.split('\n')

            for line in lines:
                if disk_name in line:
                    values = [l for l in line.split(" ") if l != '']
                    LOG.error("line: %s", values)
                    mount_point = values[-1]
                    break
            return mount_point

        except putils.ProcessExecutionError as e:
            LOG.error("query disk mount point cmd error: disk name is"
                      " %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None

    def format_disk(self, disk_name, disk_format):

        try:
            (out, err) = self._execute('mkfs.' + disk_format, disk_name,
                                       run_as_root=True)
            return disk_format

        except putils.ProcessExecutionError as e:
            LOG.error("format disk cmd error: disk name is"
                      " %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})

            return None

    def mount_disk(self, disk, mount_point):

        disk_name = disk['disk_name']
        disk_format = disk.get('disk_format')

        try:
            if disk_format:
                (out, err) = self._execute('mount', '-t', disk_format,
                                           disk_name, mount_point,
                                           run_as_root=True)
            else:
                (out, err) = self._execute('mount', disk_name, mount_point,
                                           run_as_root=True)

            disk['mount_point'] = mount_point
            return disk
        except putils.ProcessExecutionError as e:
            LOG.error("Mount disk cmd error: disk name is"
                      " %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None

    def umount_disk(self, mount_point):

        try:
            (out, err) = self._execute('umount', mount_point, run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            LOG.error("umount disk error: %s", e)
            return -1

    def remove_dir(self, dir_mame):

        try:
            (out, err) = self._execute('rm', '-rf', dir_mame,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            LOG.error("remove directory %(dir)s error: %(error)s",
                      {'dir': dir_mame, 'error': e})
            return -1

    def get_disk_info(self, disk_name):

        read_data_bs = CONF.ibs
        LOG.error("read disk info bs is: %s", read_data_bs)
        if read_data_bs is None:
            read_data_bs = 1000
        try:
            (out, err) = self._execute('dd', 'if=' + disk_name,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            LOG.error("query disk mount point cmd error: disk name is"
                      " %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None

    def make_dir(self, dir_name):
        try:
            (out, err) = self._execute('mkdir', '-p', dir_name,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            LOG.error("execute CMD 'mkdir -p %(dir_name)s' error,"
                      " error detail is %(error)s",
                      {'dir_name': dir_name, 'error': e})
            raise exception.MakeDirError(error=e)

    def fillp_start_server(self, port, protocol):

        LOG.debug("Fillp server start for %s", port)
        try:
            (out, err) = self._execute('fillp', 'start', 'server',
                                       '-p', port, '-o', protocol,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            _msg = 'Fill server start error: %s' % unicode(e)
            LOG.error(_msg)
            raise exception.FillServerError(error=_msg)

    def fill_send_data(self, address, port, src_dev, des_dev,
                       protocol, offset=0):
        LOG.debug('Fillp send data start for %(src_dev)s to %(des_dev)s',
                  {'src_dev': src_dev, 'des_dev': des_dev})
        try:
            (out, err) = self._execute('fillp', 'send',
                                       '-p', address,
                                       '-p', port,
                                       '-s', src_dev,
                                       '-t', des_dev,
                                       '-b', offset,
                                       '-o', protocol,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            _msg = 'Fillp send data error: %s' % unicode(e)
            LOG.error(_msg)
            raise exception.FillServerError(error=_msg)

    def fillp_query_status(self, service):
        LOG.debug('Fillp query status start for %(service)s',
                  {'service': service})
        try:
            (out, err) = self._execute('ps', 'aux', run_as_root=True)
            lines = out.split('\n')
            for line in lines:
                if service in line:
                    return 0
            return 1
        except putils.ProcessExecutionError as e:
            _msg = 'Fillp query status error: %s' % unicode(e)
            LOG.error(_msg)
            raise exception.FillServerError(error=_msg)

    def fillp_close_connect(self, service, protocol):
        LOG.debug('Fillp stop server start')
        try:
            (out, err) = self._execute('fillp', 'close',
                                       service, '-o', protocol,
                                       run_as_root=True)
            return out
        except putils.ProcessExecutionError as e:
            _msg = 'Fillp stop error: %s' % unicode(e)
            LOG.error(_msg)
            raise exception.FillServerError(error=_msg)

    def get_all_disk(self):
        try:
            (out, _) = self._execute('lsblk', '-lf', run_as_root=True)
            lines = out.strip().split('\n')[1:]
            rs = []
            for line in lines:
                inline = line.split(" ")
                if len(inline) > 0:
                    rs.append('/dev/' + inline[0])
            return rs
        except putils.ProcessExecutionError as e:
            LOG.error("Execute lsblk error, error detail is %(error)s",
                      {'error': e})
            raise exception.MakeDirError(error=e)
