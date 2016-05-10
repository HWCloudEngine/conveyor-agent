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

import os
import re
import stat
import time

import oslo.six as six
from oslo.config import cfg

from conveyoragent.common import processutils as putils
from conveyoragent.brick import executor
from conveyoragent.brick import exception
from conveyoragent.common import log as logging

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
        #'/\/dev\/vdb/ {print $7}'
        #(out, err) = self._execute('df', '-T', '|', 'awk', '\''+ '$1==' + '"' + disk_name + '"' +' {print $2}\'', run_as_root=True)
        #(out, err) = self._execute('df ' + '-T' + ' |' + ' grep '  + disk_name, run_as_root=True)
        try:
            disk_format = None
            (out, err) = self._execute('df', '-T', run_as_root=True)
            
            lines = out.split('\n')
              
            for line in lines:
                if disk_name in line:
                    values = [l for l in line.split(" ") if l != '']                      
                    LOG.error("line: %s", values)
                    disk_format = values[1]
                    break
            return disk_format
        
        except putils.ProcessExecutionError as e:
            
            LOG.error("query disk format cmd error: disk name is %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None

    
    def get_disk_mount_point(self, disk_name):
        '''query disk mount point.'''
        try:
            mount_point = None
            ##multi partition must add later TODO
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
            
            LOG.error("query disk mount point cmd error: disk name is %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            return None
    
    def format_disk(self, disk_name, disk_format):
        
        try:
            
            (out, err) = self._execute('mkfs.' + disk_format, disk_name, run_as_root=True)
            return disk_format
        
        except putils.ProcessExecutionError as e:
            
            LOG.error("query disk mount point cmd error: disk name is %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            
            raise exception.FormatDiskError(error = e)

    
    def mount_disk(self, disk, mount_point):
        
        disk_name = disk['des_dev_name']
        disk_format = disk['src_dev_format']        
        
        try:
            
            (out, err) = self._execute('mount', '-t', disk_format, disk_name, mount_point, run_as_root=True)
            disk['mount_point'] = mount_point
            return disk
        
        except putils.ProcessExecutionError as e:
            
            LOG.error("query disk mount point cmd error: disk name is %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
            
    
    def get_disk_info(self, disk_name):
        
        read_data_bs = CONF.ibs
        LOG.error("read disk info bs is: %s", read_data_bs)
        if read_data_bs is None:
            read_data_bs = 1000
        try:
            
            (out, err) = self._execute('dd', 'if=' + disk_name, run_as_root=True)
            return out
        
        except putils.ProcessExecutionError as e:
            
            LOG.error("query disk mount point cmd error: disk name is %(disk_name)s, error detail is %(error)s",
                      {'disk_name': disk_name, 'error': e})
    
    def make_dir(self, dir_name):
        try:
            
            (out, err) = self._execute('mkdir', '-p', dir_name, run_as_root=True)
    
            return out
        
        except putils.ProcessExecutionError as e:
            
            LOG.error("execute CMD 'mkdir -p %(dir_name)s' error, error detail is %(error)s",
                      {'dir_name': dir_name, 'error': e})
            
            raise exception.MakeDirError(error=e)


