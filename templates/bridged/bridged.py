import os
import time
from random import shuffle

from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

ALT_STARTUP_TEMPLATE = """

[startup.bridged]
name = "core.system"

[startup.bridged.args]
name = "/bin/bridged"
args = ["--rpc-addr={BRIDGED_RPC_ADDR}",
    "--network={TFCHAIND_NETWORK}", "--ethport={ETH_PORT}"]

"""


class Bridged(TemplateBase):
    version = '0.0.2'
    template_name = 'bridged'

    _DATA_DIR = '/mnt/data'
    _BACKUP_DIR = '/mnt/backups'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # bind uninstall action to the delete method
        self.add_delete_callback(self.uninstall)
        self._node_sal = j.clients.zos.get('local')

    @property
    def _container_sal(self):
        """container sal object based on the container_name created by the
        service.

        Returns:
            Container -- container the service operating on
        """

        return self._node_sal.containers.get(self._container_name)

    @property
    def _container_name(self):
        return "container-%s" % self.guid

    @property
    def _container_autostart_env(self):
        """Gets autostart environment variables required to autostart the flist
        the container booting from.

        Returns:
            dict -- Environment variables required by startup.toml
        """

        return {
            'BRIDGED_RPC_ADDR': '0.0.0.0:%s' % self.data['rpcPort'],
            'TFCHAIND_NETWORK': self.data.get('network', 'standard'),
            'ETH_PORT': str(self.data['ethPort']),
            'ETH_ACCOUNT_JSON': self.data['accountJson'],
            'ETH_ACCOUNT_PASSWORD': self.data['accountPassword'],
        }

    def _get_container(self):
        """Create container object and prepare the filesystem.

        Returns:
            Container -- container the service is operating on.
        """
        self.state.check("actions", "install", "ok")

        sp = self._node_sal.storagepools.get('zos-cache')
        fs = sp.get(self.guid)

        # prepare persistent volume to mount into the container
        node_fs = self._node_sal.client.filesystem
        vol = os.path.join(fs.path, 'wallet')
        node_fs.mkdir(vol)

        vol_backup = os.path.join(fs.path, 'backups')
        node_fs.mkdir(vol_backup)

        mounts = [{
            'source': vol,
            'target': self._DATA_DIR
        },
            {
            'source': vol_backup,
            'target': self._BACKUP_DIR
        },
        ]

        container_data = {
            'flist': self.data['bridgedFlist'],
            'mounts': mounts,
            'name': self._container_name,
        }

        freeport = self._node_sal.freeports()
        if not freeport:
            raise RuntimeError("can't reserve port.")

        hostRpcPort = self._node_sal.freeports()[0]
        container_data['ports'] = {
            str(hostRpcPort): self.data['rpcPort'],
            str(self.data['ethPort']): self.data['ethPort'],

        }
        # in case of not accountJson provided we start with the alternative startup template.
        if not self.data['accountJson']:
            container_data['config'] = {'/.startup.toml': ALT_STARTUP_TEMPLATE}

        container_data['env'] = self._container_autostart_env
        return self._node_sal.containers.create(**container_data)

    def install(self):
        """prepare presistent volume."""
        self.logger.info('installing bridged {}'.format(self.name))
        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        """Remove the persistent volume"""
        try:
            self._container_sal.stop()
        except Exception as e:
            self.logger.warning(
                "removing container on the uninstall {}".format(e))
        try:
            # cleanup filesystem used by this robot
            sp = self._node_sal.storagepools.get('zos-cache')
            fs = sp.get(self.guid)
            fs.delete()
        except ValueError:
            # filesystem doesn't exist, nothing else to do
            pass

        self.state.delete('actions', 'install')

    def upgrade(self, bridgedFlist=None):
        """Upgrade the container with an updated bridged flist this is done by
        stopping the container and respawn again with the updated flist.

        bridgedFlist: If provided, the current used flist will be replaced with the specified one
        """
        # update flist
        if bridgedFlist:
            self.data['bridgedFlist'] = bridgedFlist

        self.stop()
        self.start()

    def start(self):
        """
        Creating bridged container with the provided flist, and configure mounts for datadirs
            'flist': bridged flist,
        start  the container
        (requires install to be done first.)
        """

        self.state.check('actions', 'install', 'ok')
        self._get_container()
        self.state.set('status', 'running', 'ok')
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """stop container."""

        self._container_sal.stop()
        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')
