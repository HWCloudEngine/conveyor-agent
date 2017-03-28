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
import threading
import time

from eventlet import greenthread

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import uuidutils

from conveyoragent.brick import base
from conveyoragent.conveyoragentclient.v1 import client as agentclient
from conveyoragent.engine.common import task_status
from conveyoragent.engine.common import transformer
from conveyoragent.engine.common import transformer_state
from conveyoragent import exception
from conveyoragent import utils

migrate_manager_opts = [
    cfg.ListOpt('transformer_agents',
                default=[
                    'ftp=conveyoragent.engine.agent.ftp.ftp.FtpAgent',
                    'fillp=conveyoragent.engine.agent.fillp.fillp.FillAgent',
                    'socket=conveyoragent.engine.agent.fillp.fillp.FillAgent',
                ],
                help='DEPRECATED. each resource manager class path.'),
    cfg.StrOpt('volume_name_path',
               default="/home/.by-volume-id",
               help=''),
    cfg.IntOpt('connect_retry_num',
               default=10,
               help=''),
    cfg.IntOpt('connect_retry_interval',
               default=5,
               help=''),
    cfg.IntOpt('trans_retry_num',
               default=500,
               help=''),
    cfg.IntOpt('trans_retry_interval',
               default=5,
               help='')
]

CONF = cfg.CONF
CONF.register_opts(migrate_manager_opts)

LOG = logging.getLogger(__name__)


def agent_dict_from_config(named_agent_config, *args, **kwargs):
    """Create manager class by config file, and set key with class"""
    agent_registry = dict()

    for agent_str in named_agent_config:
        agent_type, _sep, agent = agent_str.partition('=')
        agent_class = importutils.import_class(agent)
        agent_registry[agent_type] = agent_class(*args, **kwargs)

    return agent_registry


class MigrationManager(object):

    def __init__(self, *args, **kwargs):
        """initializing the client."""
        root_helper = utils.get_root_helper()
        self.migrate_ssh = base.MigrationCmd(root_helper)

        self.agents = agent_dict_from_config(CONF.transformer_agents, self)

        self.trans_states = transformer_state.TransformerSate()

    def check_disk_exist(self, context, disk_name=None):

        stdout = self.migrate_ssh.get_disk_mount_point(disk_name)

        LOG.debug("Check disk format: %s", stdout)

    def format_disk(self, disk_name, disk_format):

        try:
            stdout = self.migrate_ssh.format_disk(disk_name, disk_format)
            return stdout
        except Exception as e:
            LOG.error("Format disk error: %s", e)
            return None

    def get_disk_format(self, context, disk_name):

        try:
            stdout = self.migrate_ssh.get_disk_format(disk_name)
            return stdout
        except Exception as e:
            LOG.error("Query disk format error: %s", e)
            return None

    def get_disk_mount_point(self, context, disk_name):

        try:
            stdout = self.migrate_ssh.get_disk_mount_point(disk_name)
            return stdout
        except Exception as e:
            LOG.error("Query disk mount point error: %s", e)
            return None

    def mount_disk(self, context, disk, mount_point):

        try:
            stdout = self.migrate_ssh.mount_disk(disk, mount_point)
            return stdout
        except Exception as e:
            LOG.error("Mount disk mount point error: %s", e)
            return None

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
        retry_interval = 1
        retrise = 10
        try:
            retry = 0
            while retry < retrise:
                rs = self.migrate_ssh.umount_disk(mount_point)
                if rs != -1:
                    break
                else:
                    retry += 1
                    time.sleep(retry_interval)

            retry = 0
            while retry < retrise:
                rs = self.migrate_ssh.remove_dir(mount_point)
                if rs != -1:
                    break
                else:
                    retry += 1

                    time.sleep(retry_interval)

            return mount_point
        except Exception as e:
            LOG.error("Force umount dir %(mount_point)s error: %(error)s",
                      {'mount_point': mount_point, 'error': e})
            return None

    def get_disk_name(self, context):
        try:
            dev = self.migrate_ssh.get_all_disk()
            return dev
        except Exception as e:
            LOG.error("Attach volume rror: %s", e)
            raise

        # volume_path = CONF.volume_name_path + '/' + volume_id
        #
        # try:
        #     dev_name = os.path.realpath(volume_path)
        #     if volume_path == dev_name:
        #         return None
        #     return dev_name
        # except Exception as e:
        #     LOG.error("Query disk name error: %s", e)
        #     return None

    def upLoadFile(self, host, port, localpath, remotepath, protocol='ftp'):
        '''up load file'''
        agent = self.agents.get(protocol)
        agent.upLoadFile(host, port, localpath, remotepath)

    def upLoadDirTree(self, host, port, localpath, remotepath, protocol='ftp'):
        '''up load dir'''
        agent = self.agents.get(protocol)
        agent.upLoadDirTree(host, port, localpath, remotepath)

    def upLoadFileExt(self, host, port, localpath, remotepath, protocol='ftp'):
        '''up load file include resuming broken transfer'''
        agent = self.agents.get(protocol)
        agent.upLoadFileExt(host, port, localpath, remotepath)

    def downLoadFile(self, host, port, localpath, remotepath, protocol='ftp'):
        '''down load file'''
        agent = self.agents.get(protocol)
        agent.downLoadFile(host, port, localpath, remotepath)

    def downLoadDirTree(self, host, port, localpath, remotepath,
                        protocol='ftp'):
        '''down load dir'''
        agent = self.agents.get(protocol)
        agent.downLoadDirTree(host, port, localpath, remotepath)

    def downLoadFileExt(self, host, port, localpath, remotepath,
                        protocol='ftp'):
        '''down load file include resuming broken transfer'''
        agent = self.agents.get(protocol)
        retry = CONF.connect_retry_num
        while retry > 0:
            try:
                r = agent.downLoadFileExt(host, port,
                                               localpath, remotepath)
                if r == 0:
                    break
            except Exception as e:
                LOG.error("manager down load ext error: %s", e)
            LOG.error("retry times: %s", retry)
            time.sleep(CONF.connect_retry_interval)
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
        LOG.debug("Copy volume start: %s", volume)
        protocol = volume.get("trans_protocol")
        if not protocol:
            LOG.error("Transformer data protocol is null.")
            return None
        task_id = None
        if 'ftp' == protocol:
            task_id = self._ftp_copy_volume(volume)
        elif protocol in ['fillp', 'socker']:
            task_id = self._fillp_copy_volume(volume, protocol)
        else:
            LOG.error("Copy volume error: protocol %s not support", protocol)
            return None

        LOG.debug("Copy volume end: %s", task_id)
        return task_id

    def _ftp_copy_volume(self, volume):
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

    def _fillp_copy_volume(self, volume, protocol):
        # 1. get sgent vm info
        src_disk_name = volume.get('src_dev_name')
        dev_disk_name = volume.get('des_dev_name')
        src_vm_url = volume.get('src_gw_url')
        des_vm_url = volume.get('des_gw_url')
        mount_dir = volume.get('src_mount_point', None)

        mount = None
        if mount_dir:
            mount = mount_dir[0]

        # 2. start fillp server
        trans_port = volume.get('trans_port')
        agent_driver = self.agents.get(protocol)
        try:
            agent_driver.start_fillp_server(trans_port, protocol)
        except Exception as e:
            _msg = "Conveyor agent start fillp server error: %s" % e
            LOG.error(_msg)
            raise exception.V2vException(message=_msg)

        # 3. start data transformer
        # splite remove gw url, get host ip and port
        src_urls = src_vm_url.split(':')
        if len(src_urls) != 2:
            LOG.error("Input source gw url error: %s", src_vm_url)
            msg = "Input Source gw url error: %s" % src_vm_url
            raise exception.InvalidInput(reason=msg)

        src_vm_ip = src_urls[0]
        src_vm_port = src_urls[1]

        des_urls = des_vm_url.split(':')
        if len(des_urls) != 2:
            LOG.error("Inpute source gw url error: %s", des_vm_url)
            msg = "Inpute source gw url error: %s" % des_vm_url
            raise exception.InvalidInput(reason=msg)

        des_ip = des_urls[0]

        try:
            # create transformer task and return task id for querying it's
            # state
            task_id = uuidutils.generate_uuid()
            task_state = task_status.TRANSFORMERING
            task = transformer.TransformerTask(task_id, task_state=task_state)
            self.trans_states.add_task(task)

            # start data transformer task thread
            args = [src_vm_ip, src_vm_port, des_ip, trans_port,
                    src_disk_name, dev_disk_name, protocol, mount]
            thread = AgentThread(self._fillp_transformer_data,
                                 self.trans_states, task_id, *args)
            thread.start()
            return task_id
        except Exception as e:
            LOG.error("Download data error: %s", e)
            raise exception.DownLoadDataError(Error=e)

    def _fillp_transformer_data(self, src_host, src_port,
                                trans_ip, trans_port,
                                src_disk, dev_disk,
                                protocol, mount):
        # 1. copy data
        try:
            agent_client = agentclient.get_birdiegateway_client(src_host,
                                                                src_port)
            agent_client.vservices.start_transformer_data(trans_ip,
                                                          trans_port,
                                                          src_disk,
                                                          dev_disk,
                                                          protocol)
            # waiting server started
            self._await_trans_server_started(src_host, src_port, protocol)
        except Exception as e:
            LOG.error("Fillp transformer data error: %s", e)
            raise exception.DownLoadDataError(error=e)

        # 2. wait data transformer finish
        agent_driver = self.agents.get(protocol)
        try:
            self._await_data_trans_status(src_host, src_port, protocol)
        except Exception as e:
            LOG.error("Await data transformer error: %s", unicode(e))
            raise
        finally:
            # 2.2 close fillp server
            if 'socket' != protocol:
                agent_driver.stop_fillp_server('server', protocol)

        # 3. mount disk to directory
        if mount:
            try:
                self.migrate_ssh.make_dir(mount)
                disk = {}
                disk['disk_name'] = dev_disk
                self.migrate_ssh.mount_disk(disk, mount)
            except Exception as e:
                LOG.error("Mount disk %(disk)s to %(dir)s error: %(error)s",
                          {'disk': dev_disk, 'dir': mount, 'error': e})
                raise

    def start_transformer_data(self, trans_ip, trans_port, src_dev, des_dev,
                               protocol='fillp'):
        agent_driver = self.agents.get(protocol)

        if not agent_driver:
            _msg = "Conveyor agent does not supprt: %s" % protocol
            LOG.error(_msg)
            raise exception.V2vException(message=_msg)

        try:
            res = agent_driver.transformer_data(trans_ip, trans_port,
                                                src_dev, des_dev, protocol)
            return res
        except Exception as e:
            _msg = "Conveyor agent transformer data error: %s" % e
            LOG.error(_msg)
            raise exception.V2vException(message=_msg)

    def fillp_transformer_data_status(self, protocol):
        agent_driver = self.agents.get(protocol)
        if not agent_driver:
            _msg = "Conveyor agent does not supprt: %s" % protocol
            LOG.error(_msg)
            raise exception.V2vException(message=_msg)

        try:
            service_name = protocol + '-client'
            res = agent_driver.query_transformer_task_status(service_name)
            return res
        except Exception as e:
            _msg = "Conveyor agent query transformer data status error: %s" % e
            LOG.error(_msg)
            raise exception.V2vException(message=_msg)

    def _await_data_trans_status(selfself, host, port, protocol):
        retries = CONF.trans_retry_num
        if retries < 0:
            LOG.warning("Treating negative config value (%(retries)s) for "
                        " 'data_transformer_retries' as 0.",
                        {'retries': retries})

        attempts = 1
        if retries >= 1:
            attempts = retries + 1
        for attempts in range(1, attempts + 1):
            cls = agentclient.get_birdiegateway_client(host, port)
            status = cls.vservices.get_data_transformer_status(protocol)
            task_status = status.get('status')
            # if noe volume data transformer failed, thos clone failed
            if 1 == task_status:
                return attempts
            elif 0 == task_status:
                LOG.debug("Fillp data transformering, waiting...")
            else:
                _msg = 'Data transformer error: fillp cmd error.'
                LOG.error(_msg)
                raise exception.DownLoadDataError(error=_msg)

            greenthread.sleep(CONF.trans_retry_interval)

        # NOTE(harlowja: Should only happen if we ran out of attempts
        raise exception.DownLoadDataError(error="Transformer data "
                                                "time out")

    def _await_trans_server_started(self, host, port, protocol):
        retries = 30
        attempts = 1
        if retries >= 1:
            attempts = retries + 1
        for attempts in range(1, attempts + 1):
            cls = agentclient.get_birdiegateway_client(host, port)
            status = cls.vservices.get_data_transformer_status(protocol)
            task_status = status.get('status')
            # if noe volume data transformer failed, thos clone failed
            if 0 == task_status:
                LOG.debug("Fillp server started.")
                return attempts
            elif 1 == task_status:
                LOG.debug("Fillp server starting, waiting...")
            else:
                _msg = 'Data transformer error: fillp cmd error.'
                LOG.error(_msg)
                raise exception.DownLoadDataError(error=_msg)

            greenthread.sleep(1)

        # NOTE(harlowja: Should only happen if we ran out of attempts
        raise exception.DownLoadDataError(error="Transformer server "
                                                "start failed")


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
