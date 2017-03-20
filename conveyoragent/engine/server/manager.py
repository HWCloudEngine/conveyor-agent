# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# Copyright 2014 Red Hat, Inc.
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
import os
import threading

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import uuidutils

from conveyoragent.brick import base
from conveyoragent.engine.common import task_status
from conveyoragent.engine.common import transformer
from conveyoragent.engine.common import transformer_state
from conveyoragent import exception
from conveyoragent import utils

migrate_manager_opts = [
    cfg.StrOpt('transformer_agent',
               default='conveyoragent.engine.agent.ftp.ftp.FtpAgent',
               help='agent to transformer  data'),
    cfg.StrOpt('volume_name_path',
               default="/home/.by-volume-id",
               help='')]

CONF = cfg.CONF
CONF.register_opts(migrate_manager_opts)

LOG = logging.getLogger(__name__)

_trans_state = {}


class MigrationManager(object):

    def __init__(self, transformer_agent=None, *args, **kwargs):
        """initializing the client."""
        root_helper = utils.get_root_helper()
        self.migrate_ssh = base.MigrationCmd(root_helper)

        if not transformer_agent:
            transformer_agent = CONF.transformer_agent

        self.agent = importutils.import_object(transformer_agent)

        self.trans_states = transformer_state.TransformerSate()

    def check_disk_exist(self, context, disk_name=None):

        stdout = self.migrate_ssh.get_disk_mount_point(disk_name)

        LOG.debug("Check disk format: %s", stdout)

    def format_disk(self, disk_name, disk_format):

        stdout = self.migrate_ssh.format_disk(disk_name, disk_format)
        LOG.debug("format disk: %s", stdout)

        return stdout

    def get_disk_format(self, context, disk_name):

        stdout = self.migrate_ssh.get_disk_format(disk_name)

        LOG.error("Query disk format: %s", stdout)

        return stdout

    def get_disk_mount_point(self, context, disk_name):

        stdout = self.migrate_ssh.get_disk_mount_point(disk_name)

        return stdout

    def mount_disk(self, context, disk, mount_point):

        stdout = self.migrate_ssh.mount_disk(disk, mount_point)

        return stdout

    def force_mount_disk(self, context, disk, mount_point):

        try:
            self.migrate_ssh.make_dir(mount_point)
            self.migrate_ssh.mount_disk(disk, mount_point)
            return mount_point
        except Exception as e:
            LOG.error("Force mount disk %(disk_name)s to dir "
                      "%(mount_point)s error: %(error)s",
                      {'disk_name': disk.get('disk_name'),
                       'mount_point': mount_point, 'error': e})
            return None

    def force_umont_disk(self, context, mount_point):
        try:
            self.migrate_ssh.umount_disk(mount_point)
            self.migrate_ssh.remove_dir(mount_point)
            return mount_point
        except Exception as e:
            LOG.error("Force umount dir %(mount_point)s error: %(error)s",
                      {'mount_point': mount_point, 'error': e})
            return None

    def get_disk_name(self, context, volume_id):

        volume_path = CONF.volume_name_path + '/' + volume_id

        try:
            dev_name = os.path.realpath(volume_path)
            if volume_path == dev_name:
                return None
            return dev_name
        except Exception as e:
            LOG.error("Query disk name error: %s", e)
            return None

    def upLoadFile(self, localpath, remotepath):
        '''up load file'''
        self.agent.upLoadFile(localpath, remotepath)

    def upLoadDirTree(self, localpath, remotepath):
        '''up load dir'''
        self.agent.upLoadDirTree(localpath, remotepath)

    def upLoadFileExt(self, localpath, remotepath):
        '''up load file include resuming broken transfer'''
        self.agent.upLoadFileExt(localpath, remotepath)

    def downLoadFile(self, localpath, remotepath):
        '''down load file'''
        self.agent.downLoadFile(localpath, remotepath)

    def downLoadDirTree(self, host, port, localpath, remotepath):
        '''down load dir'''

        self.agent.downLoadDirTree(host, port, localpath, remotepath)

    def downLoadFileExt(self, host, port, localpath, remotepath):
        '''down load file include resuming broken transfer'''
        retry = 10

        while retry > 0:
            try:
                r = self.agent.downLoadFileExt(host, port,
                                               localpath, remotepath)
                if r == 0:
                    break
            except Exception as e:
                LOG.error("manager down load ext error: %s", e)
            LOG.error("retry times: %s", retry)
            # time.sleep(5)
            retry -= 1

    def query_data_transformer_state(self, task_id):
        try:
            state = self.trans_states.get_task_state(task_id)
            return state
        except exception.V2vException as ext:
            LOG.error("Query task %(task_id)s state error: %(error)s",
                      {'task_id': task_id, 'error': ext})
            _msg = "Query task state error"
            raise exception.V2vException(message=_msg)

    def clone_volume(self, volume):

        # src_disk_name = volume.get('src_dev_name')
        dev_disk_name = volume['des_dev_name']
        disk_format = volume['src_dev_format']

        # 1. format disk
        self.migrate_ssh.format_disk(dev_disk_name, disk_format)

        # 2. make the same directory as the source vm's disk mounted
        mount_dir = volume['src_mount_point'][0]

        self.migrate_ssh.make_dir(mount_dir)

        # mount disk to the directory
        volume['disk_name'] = volume['des_dev_name']
        volume['disk_format'] = volume['src_dev_format']
        self.migrate_ssh.mount_disk(volume, mount_dir)

        # 3.download data to this disk in the directory
        remote_host = volume['src_gw_url']

        # splite remote gw url, get host ip and port
        urls = remote_host.split(':')
        if len(urls) != 2:
            LOG.error("Input source gw url error: %s", remote_host)
            msg = "Input source gw url error: " + remote_host
            raise exception.InvalidInput(reason=msg)

        host_ip = urls[0]
        host_port = urls[1]
        try:
            # create transformer task and return task id for quering its state
            task_id = uuidutils.generate_uuid()
            task_state = task_status.TRANSFORMERING
            task = transformer.TransformerTask(task_id, task_state=task_state)
            self.trans_states.add_task(task)

            # start data transformer task thread
            args = [host_ip, host_port, mount_dir, mount_dir]
            thread = AgentThread(self.downLoadDirTree,
                                 self.trans_states,
                                 task_id,
                                 *args)
            thread.start()
            return task_id
            # self.downLoadDirTree(host_ip, host_ip, mount_dir, mount_dir)
        except Exception as e:
            LOG.error("DownLoad data error: %s", e)
            raise exception.DownLoadDataError(error=e)


class AgentThread(threading.Thread):

    def __init__(self, fun, state_ops_cls, task_id, *args):
        threading.Thread.__init__(self)
        self.fun = fun
        self.args = args
        self.trans_states = state_ops_cls
        self.task_id = task_id

    def run(self):
        args = self.args
        if self.fun:
            try:
                self.fun(*args)
                self.trans_states.update_state(self.task_id,
                                               task_status.FINISHED)
            except Exception as e:
                self.trans_states.update_state(self.task_id, task_status.ERROR)
                LOG.error("Conveyor agent operator %(ops)s error: %(error)s",
                          {'ops': self.fun, 'error': e})
                msg = "Operator %s error" % self.fun
                raise exception.V2vException(message=msg)
