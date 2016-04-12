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
import time
import random
from eventlet import greenthread

import oslo.six as six
from oslo.config import cfg

from conveyoragent.common import importutils
from conveyoragent.common import log as logging
from conveyoragent.brick import base
from conveyoragent import utils
from conveyoragent import exception

migrate_manager_opts = [
    cfg.StrOpt('transformer_agent',
               default='conveyoragent.engine.agent.ftp.ftp.FtpAgent',
               help='agent to transformer  data'),
                        
    cfg.StrOpt('device_link_path',
               default='/home/.gy-volume-id/',
               help='volume directory'),
]

CONF = cfg.CONF
CONF.register_opts(migrate_manager_opts)

LOG = logging.getLogger(__name__)

class MigrationManager(object):
    
    def __init__(self, transformer_agent=None, *args, **kwargs):
        """initializing the client."""
        root_helper = utils.get_root_helper()
        self.migrate_ssh = base.MigrationCmd(root_helper)
        
        if not transformer_agent:
            transformer_agent = CONF.transformer_agent
            
        self.agent = importutils.import_object(transformer_agent)        
    
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
    
    def mount_disk(self, context, disk_name, mount_point):
        
        stdout = self.migrate_ssh.mount_disk(disk_name, mount_point)
        
        return stdout
    
    def get_disk_name(self, volume_id):
        pass
    
    
    
    def upLoadFile(self, localpath, remotepath):
        ''' up load file'''
        self.agent.upLoadFile(localpath, remotepath)
        
        

    def upLoadDirTree(self, localpath, remotepath):
        '''up load dir'''
        
        self.agent.upLoadDirTree(localpath, remotepath)
        
    
    def upLoadFileExt(self, localpath, remotepath):
        '''up load file include resuming broken transfer'''
        self.agent.upLoadFileExt(localpath, remotepath)
        
        
    def downLoadFile(self, localpath, remotepath):
        ''' down load file'''
        self.agent.downLoadFile(localpath, remotepath)
        
        
    def downLoadDirTree(self, host, port, localpath, remotepath):
        ''' down load dir'''
        
        self.agent.downLoadDirTree(host, port, localpath, remotepath)
        
    
    def downLoadFileExt(self, localpath, remotepath):
        ''' down load file include resuming broken transfer'''
        retry = 10
        
        while retry > 0:
            try:
                r = self.agent.downLoadFileExt(localpath, remotepath)
                
                if r == 0:
                    break 

            except Exception, e:
                LOG.error("manager down load ext error: %s", e)
            
            
            LOG.error("retry times: %s", retry)
            #time.sleep(5)
            retry -= 1
            
    
    
    def clone_volume(self, volume):
        
        src_disk_name = volume.get('src_dev_name')
        dev_disk_name = volume['des_dev_name']
        disk_format = volume['src_dev_format']
        
        #1. format disk
        self.migrate_ssh.format_disk(dev_disk_name, disk_format)
        
        #2. make the same directory as the source vm's disk mounted
        mount_dir = volume['src_mount_point'][0]

        self.migrate_ssh.make_dir(mount_dir)
       
        #mount disk to the directory
        self.migrate_ssh.mount_disk(volume, mount_dir)
        
        #3.download data to this disk in the directory
        remote_host = volume['src_gw_url']
        
        #splite remote gw url, get host ip and port
        urls = remote_host.split(':')
        if len(urls) != 2:
            LOG.error("Input source gw url error: %s", remote_host)
            msg = "Input source gw url error: " + remote_host
            raise exception.InvalidInput(reason=msg)
            
        host_ip = urls[0]
        host_port = urls[1]
        try:
            self.downLoadDirTree(host_ip, host_port, mount_dir, mount_dir)
        except Exception as e:
            LOG.error("DownLoad data error: ")
            raise exception.DownLoadDataError(error=e)




