# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import threading

from oslo_config import cfg
from oslo_log import log as logging

from conveyoragent.brick import base
from conveyoragent import exception
from conveyoragent import utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class FillAgent(object):
    def __init__(self, host=None, port=None, user=None, passwd=None,
               timeout=-999):
        self.host = host
        self.port = port
        root_helper = utils.get_root_helper()
        self.cmd_process = base.MigrationCmd(root_helper)

    def start_fillp_server(self, address, port, des_dev, protocol):
        try:
            args = [address, port, des_dev, protocol]
            fillp_thread = AgentThread(self._start_fillp_server, *args)
            fillp_thread.start()
            return fillp_thread
        except Exception as e:
            _msg = "Start fillp service failed: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)

    def _start_fillp_server(self, address, port, des_dev, protocol):
        try:
            self.cmd_process.fillp_start_server(address, port,
                                                des_dev, protocol)
        except Exception as e:
            _msg = "Start fillp service failed: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)

    def transformer_data(self, address, port, src_dev, des_dev, protocol):
        try:
            args = [address, port, src_dev, des_dev, protocol]
            fillp_thread = AgentThread(self._transformer_data, *args)
            fillp_thread.start()
            return fillp_thread
        except Exception as e:
            _msg = "Fillp transformer data failed: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)

    def _transformer_data(self, address, port, src_dev, des_dev, protocol):
        try:
            res = self.cmd_process.fill_send_data(address, port, src_dev,
                                                  des_dev, protocol)
            return res
        except Exception as e:
            _msg = "Fillp transformer data failed: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)

    def query_transformer_task_status(self, protocol):
        try:
            status = self.cmd_process.fillp_query_status(protocol)
            return status
        except Exception as e:
            _msg = "Fillp query transfer data failed: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)

    def stop_fillp_server(self, service, protocol):
        try:
            self.cmd_process.fillp_close_connect(service, protocol)
        except Exception as e:
            _msg = "Fillp stop server errror: %s" % unicode(e)
            LOG.error(_msg)
            raise exception.DownLoadDataError(error=_msg)


class AgentThread(threading.Thread):
    def __init__(self, fun, *args):
        threading.Thread.__init__(self)
        self.fun = fun
        self.args = args

    def run(self):
        args = self.args
        if self.fun:
            try:
                self.fun(*args)
            except Exception as e:
                LOG.error("Conveyor agent operator %(ops)s error: %(error)s",
                          {'ops': self.fun, 'error': e})
                msg = 'Operator %s error' % self.fun
                raise exception.V2vException(message=msg)
