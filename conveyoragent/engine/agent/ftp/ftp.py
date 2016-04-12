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

import os
import time

from oslo.config import cfg
from conveyoragent.common import log as logging
from conveyoragent.brick import base
from conveyoragent import utils

from conveyoragent.engine.agent.ftp import ftplib


ftp_paras = [
    cfg.IntOpt('ftp_port',
               default=21,
               help=''),
    cfg.StrOpt('ftp_host',
               default="0.0.0.0",
               help=''),
    cfg.StrOpt('user_name',
               default="root",
               help=''),
    cfg.StrOpt('user_passwd',
               default="magento",
               help=''),             
    cfg.IntOpt('max_lines',
               default=8192,
               help=''),
    cfg.IntOpt('ftp_timeout',
               default=-999,
               help=''),
    cfg.IntOpt('ftp_buffersize',
               default=1024,
               help=''),  
                
]

CONF = cfg.CONF
CONF.register_opts(ftp_paras)

LOG = logging.getLogger(__name__)


class FtpAgent(object):
    
    def __init__(self, host=None, port=None, user=None, passwd=None, timeout=-999):
        
        self.ftp = ftplib.FTP()
        
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.timeout = timeout
        
        self.connect = None
        
        if not host:
            self.host = CONF.ftp_host
            
        if not port:
            self.port = CONF.ftp_port
            
        if not user:
            self.user = CONF.user_name
            
        if not passwd:
            self.passwd = CONF.user_passwd
            
            
        #self.connect = self.connectFtp(host, port, user, passwd, timeout)
    
    def connectFtp(self, host, port, user, passwd, timeout):
        '''set up connection to ftp server'''
    
        try:
            self.ftp.connect(host, port, timeout)
            
        except Exception, e:
            
            LOG.error("Ftp connect error: %s", e)
            
            return None
            
        else:
            
            try:
                self.ftp.login(user, passwd)
            except Exception, e:
                LOG.error("Ftp login error: %s", e)
                return None
            else:    
                LOG.debug("ftp login success")
                self.connect = True
            
        
    def downLoadFile(self, localpath, remotepath):
        """down file.

            :param localpath: storage file in local path 
                   remotepath: file in remote host path

        """
        LOG.debug("ftp down load file start")
        if not self.connect:
            self.connectFtp(self.host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
        
        bufsize = CONF.ftp_buffersize
        try:
            fp = open(localpath,'wb')
            self.ftp.retrbinary('RETR ' + remotepath, fp.write, bufsize)
        
        except Exception, e:
            
            LOG.error("ftp down load file error: %s", e)
            
        finally:            
            fp.close()
        
        LOG.debug("ftp down load file end")
    
    def downLoadDirTree(self, host, port, localpath, remotepath):
        ''''''
        LOG.debug("Ftp down directory start")
        if not host:
            host = self.host
            
        if not port:
            self.port = port

        if not self.connect:
            self.connectFtp(host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
            
        if not os.path.isdir(localpath):
            os.makedirs(localpath)
            
        self.ftp.cwd(remotepath)
        
        #list all dir or file in remote device
        remoteNames = self.ftp.nlst()
        
        for remote in remoteNames:
            
            local = os.path.join(localpath, remote)
            
            if self._isDir(remote):
                             
                self.downLoadDirTree(host, self.port,local, remote)                
            else:
                self.downLoadFile(local, remote)
                
        self.ftp.cwd( ".." )
        
        LOG.debug("Ftp down directory end")
        return

    
    def upLoadFile(self, localpath, remotepath):
        
        if not self.connect:
            self.connectFtp(self.host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
            
        
        bufsize = CONF.ftp_buffersize
        
        try:  
            fp = open(localpath, 'rb')
            self.ftp.storbinary('STOR '+ remotepath , fp, bufsize)
        except Exception, e:
            LOG.error("")
        finally:
            fp.close()
    
    def upLoadDirTree(self, localDir, remoteDir):
        
        ''''''

        if not self.connect:
            self.connectFtp(self.host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
            
        if os.path.isdir(localDir) == False:
            return False
        
        localNames = os.listdir(localDir)
        
        #cd to remote dir
        self.ftp.cwd(remoteDir)
        
        for local in localNames:
            
            src = os.path.join(localDir, local)
            
            if os.path.isdir(src):
                
                self.ftp.mkd(local)
                
                self.upLoadDirTree(src, local)
            else:
                self.upLoadFile(src, local)
                
        self.ftp.cwd( ".." )
        return
    
    
    def downLoadFileExt(self, localpath, remotepath):
        '''Down load file include resuming broken transfer'''
        if not self.connect:
            self.connectFtp(self.host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
        
        #set active mode for data transfers
        self.ftp.set_pasv(0)
        
        dires = self._splitpath(remotepath)
        
        #change input dir in remote device
        if dires[0]:
            self.ftp.cwd(dires[0])
        
        #cal down load file size
        remotefile=dires[1]        
        fsize = self.ftp.size(remotefile)
        
        #if down load file is empty
        if fsize == 0:
            LOG.debug("")
        
        #if local device exist the same file, and cal this file size    
        lsize=0L
        if os.path.exists(localpath):
            lsize=os.stat(localpath).st_size
        
        #if local device file size larger than remote   
        if lsize >= fsize:
            LOG.debug("")
            return
        
        #Each transmission file size
        blocksize = CONF.ftp_buffersize ** 2
        
        #set file transmission as binary
        self.ftp.voidcmd('TYPE I')
        
        #Down load file beginning in lsize location, so as resuming broken transfer
        conn = self.ftp.transfercmd('RETR ' + remotefile, lsize)
        
        lwrite = open(localpath,'ab')
        
        #Here can be changed to transmission some times
        while True:
            time.sleep(3)
            data=conn.recv(blocksize)
            if not data:
                break
            lwrite.write(data)
        lwrite.close()
        try:
            self.ftp.voidcmd('NOOP')
            self.ftp.voidresp()
        except Exception, e:
            
            LOG.error("down load ext error: %s", e)
            self.ftp.disconnect()
            self.connect = None
        conn.close()
        
        return 0
    
    def upLoadFileExt(self, localpath, remotepath, callback=None):
        '''Up load file include resuming broken transfer'''
        if not self.connect:
            self.connectFtp(self.host, self.port, self.user, self.passwd, self.timeout)
            
            #reconnect policy add later
            if not self.connect:
                LOG.error("connect ftp failed")
                return
        
        
        remote = self._splitpath(remotepath)
        
        self.ftp.cwd(remote[0])
        
        rsize = 0L
        try:
            rsize = self.ftp.size(remote[1])
        except Exception, e:
            LOG.debug("")
        
        if (rsize == None):
            rsize = 0L
        lsize = os.stat(localpath).st_size
        
        if (rsize >= lsize):
            LOG.debug("")
        if (rsize < lsize):
            localf = open(localpath,'rb')
            localf.seek(rsize)
            self.ftp.voidcmd('TYPE I')
            datasock = ''
            esize = ''
            
            try:                 
                datasock, esize = self.ftp.ntransfercmd("STOR "+remote[1],rsize)
            except Exception, e:                
                return
            
            cmpsize = rsize
            blocksize = CONF.ftp_buffersize ** 2
            
            while True:
                buf=localf.read(blocksize)
                if not len(buf):                     
                    break               
                datasock.sendall(buf)                 
                if callback:                     
                    callback(buf)                
                    cmpsize += len(buf)                
                if cmpsize == lsize:                    
                    break
            datasock.close()
            localf.close()
            self.ftp.voidcmd('NOOP')
            self.ftp.voidresp()
    
    def destoryConnection(self):
        
        if self.connect is None:
            
            return
        
        try:
            
            self.ftp.quit()
            
            self.connect = None
        
        except Exception, e:
            LOG.error("")
    
    
    
    def _show(self, pathList):
        
        result = pathList.lower().split(" ")
        
        if self.path in result and result[0][0] == 'd':
            self.bIsDir = True
     
    def _isDir(self, path):
        self.bIsDir = False
        self.path = path
        self.ftp.retrlines('LIST', self._show)
        return self.bIsDir
    
    def _splitpath(self, path):
        
        position = path.rfind('/')
        return (path[:position+1], path[position+1:]) 

    
    

        
    
