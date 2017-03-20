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

"""The conveyoragent api."""

from webob import exc

from oslo_log import log as logging

from conveyoragent.engine.api.view import v2vgatewayservices as services_view
from conveyoragent.engine.api.wsgi import wsgi
from conveyoragent.engine.server import manager
from conveyoragent.i18n import _

LOG = logging.getLogger(__name__)


class V2vGateWayServiceController(wsgi.Controller):
    """The Volumes API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.viewBulid = services_view.ViewBuilder()
        self.migration_manager = manager.MigrationManager()
        super(V2vGateWayServiceController, self).__init__()

    def show(self, req, id):
        """Return data about the given resource."""
        LOG.debug("Query task state start: %s", id)

        try:
            state = self.migration_manager.query_data_transformer_state(id)
            LOG.debug("Query task state end: %s", id)
            return self.viewBulid.show(state)
        except Exception as e:
            LOG.error("Query task %(task_id)s state error: %(error)s",
                      {'task_id': id, 'error': e})
            msg = _("Query data transformer task state failed")
            raise exc.HTTPBadRequest(explanation=msg)

    def delete(self, req, id):
        """Delete resource."""
        LOG.debug("delete test!")
        return

    def index(self, req):
        """Returns a summary list of resource."""
        pass

    def detail(self, req):
        """Returns a detailed list of resource."""
        LOG.debug("detail test!")
        return

    def create(self, req, body):
        """DownLoad data from source volume"""

        if not self.is_valid_body(body, 'clone_volume'):
            LOG.debug("V2v gateway download data request not key:clone_volume")
            raise exc.HTTPUnprocessableEntity()
        volume = body['clone_volume']

        try:
            state = self.migration_manager.clone_volume(volume)

            return self.viewBulid.create(state)

        except Exception as e:
            LOG.error("Clone volume data error: %s", e)
            msg = _("clone volume data failed")
            raise exc.HTTPBadRequest(explanation=msg)

    def update(self, req, id, body):
        """Update a resource."""

        pass


def create_resource(ext_mgr):
    return wsgi.Resource(V2vGateWayServiceController(ext_mgr))
