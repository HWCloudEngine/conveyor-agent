# Copyright 2011 OpenStack Foundation
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

from conveyoragent.common import log as logging
from conveyoragent import context
from conveyoragent.engine.api import extensions
from conveyoragent.engine.api.wsgi import wsgi
from conveyoragent.engine.server import manager

LOG = logging.getLogger(__name__)

defaultContext = context.get_admin_context()


class MigrationController(wsgi.Controller):

    def __init__(self):

        self.migration_manager = manager.MigrationManager()
        super(MigrationController, self).__init__()

    def index(self):
        pass


class MigrationActionController(wsgi.Controller):

    def __init__(self, ext_mgr=None, *args, **kwargs):
        super(MigrationActionController, self).__init__(*args, **kwargs)
        self.migration_manager = manager.MigrationManager()
        self.ext_mgr = ext_mgr

    @wsgi.action('checkDisk')
    def _check_disk_exist(self, req, id, body):

        disk_name = body['checkDisk']['disk_name']

        out = self.migration_manager.check_disk_exist(defaultContext,
                                                      disk_name)

        return out

    @wsgi.action('getDiskFormat')
    def _get_disk_format(self, req, id, body):

        disk_name = body['getDiskFormat']['disk_name']

        LOG.debug("Query disk start format: %s", disk_name)

        out = self.migration_manager.get_disk_format(defaultContext,
                                                     disk_name)

        resp = {"disk_format": out}
        LOG.debug("Query disk format end: %s", out)
        return resp

    @wsgi.action('formatDisk')
    def _format_disk(self, req, id, body):

        disk_name = body['formatDisk']['disk_name']

        disk_format = body['formatDisk']['disk_format']

        out = self.migration_manager.format_disk(defaultContext, disk_name,
                                                 disk_format)
        resp = {"format_disk": out}
        return resp

    @wsgi.action('getDiskMountPoint')
    def _get_disk_mount_point(self, req, id, body):

        disk_name = body['getDiskMountPoint']['disk_name']
        LOG.debug("Query disk %s mount point start", disk_name)
        out = self.migration_manager.get_disk_mount_point(defaultContext,
                                                          disk_name)
        resp = {"mount_point": out}

        LOG.debug("Query disk %(disk_name)s mount point %(mount_point)s end",
                  {'disk_name': disk_name, 'mount_point': out})
        return resp

    @wsgi.action('getDiskName')
    def _get_disk_name(self, req, id, body):

        volume_id = body['getDiskName']['volume_id']
        LOG.debug("Query volume %s dev name start", volume_id)
        out = self.migration_manager.get_disk_name(defaultContext, volume_id)
        resp = {"dev_name": out}

        LOG.debug("Query volume %(volume_id)s dev name %(dev_name)s end",
                  {'volume_id': volume_id, 'dev_name': out})
        return resp

    @wsgi.action('mountDisk')
    def _mount_disk(self, req, id, body):

        disk = body['mountDisk']['disk']

        mount_point = body['mountDisk']['mount_point']

        out = self.migration_manager.mount_disk(defaultContext, disk,
                                                mount_point)
        resp = {"mount_disk": out}
        return resp

    @wsgi.action('forceMountDisk')
    def _force_mount_disk(self, req, id, body):

        disk_name = body['forceMountDisk']['disk']

        mount_point = body['forceMountDisk']['mount_point']

        out = self.migration_manager.force_mount_disk(defaultContext,
                                                      disk_name,
                                                      mount_point)
        resp = {"mount_disk": out}
        return resp

    @wsgi.action('forceUmountDisk')
    def _force_umount_disk(self, req, id, body):

        mount_point = body['forceUmountDisk']['mount_point']

        out = self.migration_manager.force_umont_disk(defaultContext,
                                                      mount_point)
        resp = {"umount_disk": out}
        return resp


class Migration(extensions.ExtensionDescriptor):
    """Enable admin actions."""

    name = "Migration"
    alias = "conveyoragent-migration"
    namespace = "http://docs.openstack.org/v2vgateway/ext/migration/api/v1"
    updated = "2016-01-29T00:00:00+00:00"

    # define new resource
    def get_resources(self):
        resources = []
        controller = MigrationController()
        resource = extensions.ResourceExtension('conveyoragent-migration',
                                                controller)
        resources.append(resource)
        return resources

    # extend exist resource
    def get_controller_extensions(self):
        controller = MigrationActionController(self.ext_mgr)
        extension = extensions.ControllerExtension(self, 'v2vGateWayServices',
                                                   controller)
        return [extension]
