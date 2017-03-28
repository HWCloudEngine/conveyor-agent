# Copyright 2017 Huawei, Inc.
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
Handles all requests relating to volumes + cinder.
"""

import json
import requests
import uuid

from oslo_config import cfg
from oslo_log import log as logging

conveyor_opts = [
    cfg.StrOpt('conveyor_url',
               default='',
               help='conveyor service url for updating config file'),
]

CONF = cfg.CONF
CONF.register_opts(conveyor_opts)

LOG = logging.getLogger(__name__)


class API(object):
    """API for interacting with conveyor manager."""

    def update_configs(self, **configs):
        def _get_conveyor_url():
            tenant_id = uuid.uuid4().hex
            return (CONF.conveyor_url.replace('$(', '%(')
                    + '/configurations') % {'tenant_id': tenant_id}
        data = {"configurations": configs}
        LOG.info("Update configurations with url %s, data: %s",
                 _get_conveyor_url(), data)
        r = requests.post(_get_conveyor_url(),
                          data=json.dumps(data),
                          headers={'content-type': 'application/json'},
                          timeout=3)
        msg = "Update configuration result: status %d, body %s" \
              % (r.status_code, r.text)

        if r.status_code >= 400:
            LOG.error(msg)
        else:
            LOG.debug(msg)
