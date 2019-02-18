"""Blockcreator template.

used to deploy blockcreator container from autostartable flist.
"""

import os
import time
from random import shuffle
import gevent
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError
import netaddr


class BlockCreator(TemplateBase):
    """Blockcreator template used to deploy blockcreator tfchaind on a
    container using 0-robot."""

    version = '0.0.2'
    template_name = 'block_creator'

    _DATA_DIR = '/mnt/data'
    _BACKUP_DIR = '/mnt/backups'

    def __init__(self, name=None, guid=None, data=None):
        """Initialize blockcreator template."""
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
        return self._node_sal.containers.get(self._container_name)

    @property
    def _container_name(self):
        return "container-%s" % self.guid

    def get_rpc_addr(self):
        """Get RPC address of the tfchaind server."""
        return "http://{}:{}".format(self._node_sal.addr, self.data['rpcPort'])

    def get_api_addr(self):
        """Get API address endpoint for the tfchaind.

        Returns:
            str -- IP for the tfchaind
        """
        ip = self._container_sal.default_ip("nat0")
        return "http://{}:{}".format(str(ip.ip), self.data['apiPort'])

    @property
    def _container_autostart_env(self):
        """Get autostart environment variables required to autostart the flist
        the container booting from.

        Returns:
            dict -- Environment variables required by startup.toml
        """
        return {
            'TFCHAIND_RPC_ADDR': "0.0.0.0:{}".format(self.data['rpcPort']),
            'TFCHAIND_API_ADDR': "0.0.0.0:{}".format(self.data['apiPort']),
            'TFCHAIND_DATA_DIR': self._DATA_DIR,
            'TFCHAIND_NETWORK':  self.data.get('network', 'standard'),
        }

    @property
    def _client_sal(self):
        """Get tfchain client sal object.

        Returns:
            [TFChainClient] -- tfchain client for the running tfchaind
        """
        if self.__client_sal is None:
            kwargs = {
                'name': self.name,
                'container': self._container_sal,
                'api_addr': self.get_api_addr(),
                'wallet_passphrase': self.data['walletPassphrase'],
            }
            self.__client_sal = j.sal_zos.tfchain.client(**kwargs)
        return self.__client_sal

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

        mounts = [
            {
                'source': vol,
                'target': self._DATA_DIR
            },
            {
                'source': vol_backup,
                'target': self._BACKUP_DIR
            },
        ]

        container_data = {
            'flist': self.data['tfchainFlist'],
            'mounts': mounts,
            'name': self._container_name,
        }
        freeport = self._node_sal.freeports()
        if not freeport:
            raise RuntimeError("can't reserve port.")

        hostRpcPort = self._node_sal.freeports()[0]
        container_data['ports'] = {
            str(hostRpcPort): self.data['rpcPort'],
        }
        container_data['env'] = self._container_autostart_env
        return self._node_sal.containers.create(**container_data)

    def install(self):
        """Prepare the persistent volume of the wallet."""
        self.logger.info('installing tfchaind %s', self.name)
        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
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

        self.state.delete('actions', 'install')

    def upgrade(self, tfchainFlist=None):
        """Upgrade the container with an updated flist.

        this is done by stopping the container and respawn again with the updated flist

        tfchainFlist: If provided, the current used flist will be replaced with the specified one
        """
        # update flist
        if tfchainFlist:
            self.data['tfchainFlist'] = tfchainFlist

        self.stop()
        # restart daemon in new container
        self.start()

    @retry((RuntimeError), tries=5, delay=2, backoff=2)
    def _wallet_init(self):
        """Initialize the wallet with a new seed and password."""
        try:
            self.state.check('wallet', 'init', 'ok')
            return
        except StateCheckError:
            pass

        self.logger.info('initializing wallet %s', self.name)
        self.logger.info("wallet endpoint: %s", self._client_sal._curl.addr)
        while True:
            try:
                self._client_sal.wallet_init()
            except RuntimeError as e:
                self.logger.info("wallet not initialized yet: %s", str(e))
                gevent.sleep(1)
            else:
                break
        self.data['walletSeed'] = self._client_sal.recovery_seed
        self.state.set('wallet', 'init', 'ok')

    def start(self):
        """Start container and initialize unencrypted wallet."""
        self.state.check('actions', 'install', 'ok')
        container = self._get_container()
        self.state.set('status', 'running', 'ok')
        self._wallet_init()
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """Stop tfchain daemon container."""
        self.logger.info('Stopping tfchain daemon %s', self.name)
        self._container_sal.stop()
        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')
        self.state.delete('wallet', 'init')

    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def wallet_address(self):
        """Load wallet address into the service's data."""
        self.state.check('wallet', 'init', 'ok')

        if not self.data.get('walletAddr'):
            self.data['walletAddr'] = self._client_sal.create_new_wallet_address()
        return self.data['walletAddr']

    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def wallet_amount(self):
        """Return the amount of token in the wallet."""
        self.state.check('wallet', 'init', 'ok')
        self.state.check('status', 'running', 'ok')
        return self._client_sal.wallet_amount()

    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def consensus_stat(self):
        """Return information about the state of consensus."""
        self.state.check('wallet', 'init', 'ok')
        self.state.check('status', 'running', 'ok')
        return self._client_sal.consensus_stat()

    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def report(self):
        """Return a full report.

        - wallet_status = string [locked/unlocked]
        - block_height = int
        - active_blockstakes = int
        - network = string [devnet/testnet/standard]
        - confirmed_balance = int
        - connected_peers = int
        - address = string
        """
        self.state.check('wallet', 'init', 'ok')
        self.state.check('status', 'running', 'ok')
        report = self._client_sal.get_report()

        report["network"] = self.data["network"]
        peers = report.get("connected_peers", 0)
        if isinstance(peers, list):
            report["connected_peers"] = len(peers)
        else:
            report["connected_peers"] = int(peers)

        return report
