# Copyright 2011 Justin Santa Barbara
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

import mock
import testtools

from conveyoragent.common import config
from conveyoragent import context
from conveyoragent.engine.api import extensions
from conveyoragent.engine.api.v1 import v2vgatewayservices
from conveyoragent.engine.server import manager

CONF = config.CONF


class TestV2vGateWayServiceController(testtools.TestCase):

    def setUp(self):
        super(TestV2vGateWayServiceController, self).setUp()
        self.ext_mgr = extensions.ExtensionManager()
        self.ext_mgr.extensions = {}
        self.ctx = context.RequestContext('fake', 'fake', is_admin=False)
        self.agent_service = \
            v2vgatewayservices.V2vGateWayServiceController(self.ext_mgr)

    @mock.patch.object(manager.MigrationManager, 'clone_volume')
    def test_create(self, mock_clone_volume):
        body = {'clone_volume': {'src_dev_name': 'fake-src-dev',
                                 'des_dev_name': 'fake-dev-dev',
                                 'src_dev_format': 'ext4',
                                 'src_mount_point': '/fake',
                                 'src_gw_url': '127.0.0.1:9998',
                                 'des_gw_url': '127.0.0.1:9998',
                                 'trans_protocol': 'socket',
                                 'trans_port': '1234'}
                }
        mock_clone_volume.return_value = 'task-001'
        result = self.agent_service.create(self.ctx, body)
        self.assertEqual('task-001', result['body']['task_id'])
