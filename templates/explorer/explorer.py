import os
import time
import io
from random import shuffle

from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

BLOCK_CREATOR_UID = 'github.com/threefoldfoundation/tfchain-templates/block_creator/0.0.2'


class Explorer(TemplateBase):
    version = '0.0.2'
    template_name = 'explorer'

    _DATA_DIR = '/mnt/data'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # bind uninstall action to the delete method
        self.add_delete_callback(self.uninstall)
        self._node_sal = j.clients.zos.get('local')
        self.__client_sal = None

        # wallet_passphrase = self.data.get('walletPassphrase')
        # if not wallet_passphrase:
        #     self.data['walletPassphrase'] = j.data.idgenerator.generateGUID()

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

        blockcreator_api_addr = self._block_creator.schedule_action(
            'get_api_addr').wait().result
        return {
            'TFCHAIND_RPC_ADDR': '0.0.0.0:%s' % self.data['rpcPort'],
            'TFCHAIND_API_ADDR': '0.0.0.0:%s' % self.data['apiPort'],
            'TFCHAIND_DATA_DIR': self._DATA_DIR,
            'TFCHAIND_NETWORK':  self.data.get('network', 'standard'),
            'BLOCK_CREATOR_API_ADDR': blockcreator_api_addr,
            'TFCHAIND_ETHBOOTNODES': self.data["ethbootnodes"],
        }

    def _get_container(self):
        """Create container object and prepare the filesystem.

        Returns:
            Container -- container the service is operating on.
        """
        self.state.check("actions", "install", "ok")

        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        # prepare persistent volume to mount into the container
        node_fs = self._node_sal.client.filesystem
        vol = os.path.join(fs.path, 'wallet')
        node_fs.mkdir(vol)
        caddy = os.path.join(fs.path, 'caddy-certs')
        node_fs.mkdir(caddy)

        mounts = [
            {
                'source': vol,
                'target': self._DATA_DIR
            },
            {
                'source': caddy,
                'target': '/.caddy/'
            }
        ]

        container_data = {
            'flist': self.data['explorerFlist'],
            'mounts': mounts,
            'name': self._container_name,
        }

        container_data['ports'] = {
            '80': 80,
            '443': 443,
        }
        container_data['env'] = self._container_autostart_env

        # remove write_caddyfile calls once this works
        container_data['config'] = {
            '/var/www/explorer/caddy/Caddyfile': self._get_caddyfile()}
        self._container = self._node_sal.containers.create(**container_data)
        return self._container

    @property
    def _block_creator_name(self):
        return "block_creator-{}".format(self.guid)

    def _create_blockcreator(self):
        """Creates blockcreator service to be used internally by explorer.

        Returns:
            Service -- Blockcreator service
        """

        blockcreator_data = {
            'node': self._node_sal.name,
            'rpcPort': self.data['rpcPort'],
            'apiPort': self.data['apiPort'],
            'walletSeed': self.data['walletSeed'],
            'walletPassphrase': self.data['walletPassphrase'],
            'walletAddr': self.data['walletAddr'],
            'network': self.data['network'],
        }
        return self.api.services.find_or_create(template_uid=BLOCK_CREATOR_UID, service_name=self._block_creator_name, data=blockcreator_data)

    @property
    def _block_creator(self):
        try:
            return self.api.services.get(template_uid=BLOCK_CREATOR_UID, name=self._block_creator_name)
        except ServiceNotFoundError:
            raise

    def install(self):
        """prepare presistent volume."""
        self.logger.info('installing tftfaucet %s', self.name)
        self._create_blockcreator()
        self._block_creator.schedule_action('install').wait()

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        """Remove the persistent volume of the wallet, and delete the
        container."""
        """Remove the persistent volume of the wallet."""

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

        self._block_creator.schedule_action('uninstall').wait()
        self.state.delete('actions', 'install')

    def start(self):
        """start both tfchain daemon and client."""
        self.state.check('actions', 'install', 'ok')
        self._block_creator.state.check('actions', 'install', 'ok')
        self._block_creator.schedule_action('start').wait()

        container = self._get_container()

        # FIXME: remove when config parameter is supported for container create
        self.write_caddyfile()

        self.state.set('status', 'running', 'ok')
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """stop tftaucet."""
        self.logger.info('Stopping faucet %s', self.name)
        self._container_sal.stop()

        self._block_creator.schedule_action('stop').wait()

        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def upgrade(self, explorerFlist=None):
        """upgrade the container with an updated flist this is done by stopping
        the container and respawn again with the updated flist.

        explorerFlist: If provided, the current used flist will be replaced with the specified one
        """
        # update flist
        if explorerFlist:
            self.data['explorerFlist'] = explorerFlist

        self.stop()
        # restart daemon in new container
        self.start()

    def _get_caddyfile(self):
        """formats caddy file with service domain to enable https."""
        url = self.data.get('domain')
        url = url.lstrip("https://").lstrip("http://")

        # Caddyfile template
        template = """
http://{url} {{
    redir {url}
}}

https://{url} {{
    root ../public

    header / {{
	    Access-Control-Allow-Origin  *
        Access-Control-Allow-Methods  *
    }}

    proxy /explorer {daemon_api_url} {{
        header_upstream User-Agent Rivine-Agent
    }}

    proxy /transactionpool/transactions {daemon_api_url} {{
        header_upstream User-Agent Rivine-Agent
    }}

    log stdout
    tls support@threefoldtoken.com
}}""".format(url=url, daemon_api_url=self._container_autostart_env['BLOCK_CREATOR_API_ADDR'])
        return template

    # FIXME: remove when new robot flist is created, and send caddy file using config instead of upload_content
    def write_caddyfile(self):
        """Writes the caddy file to enable https."""
        template = self._get_caddyfile()
        template_bytes = template.encode()

        # location for caddyfile
        config_location = '/var/www/explorer/caddy/Caddyfile'
        # Upload file
        self._container_sal.upload_content(config_location, template_bytes)
