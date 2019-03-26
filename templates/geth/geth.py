import os
import time
import io
import requests
from random import shuffle
import uuid

from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

ALT_STARTUP_TEMPLATE = """

[startup.geth]
name = "core.system"

[startup.geth.args]
name = "/sandbox/bin/geth"
args = ["--{GETH_NETWORK}", "--verbosity={GETH_VERBOSITY}",
    "--lightserv={GETH_LIGHTSERV}", "--nat={GET_NAT}", "--{GETH_V5DISC}", 
    "--syncmode={GETH_SYNCMODE}", "--datadir={GETH_DATADIR}", "--rpc", 
    "--rpcaddr=0.0.0.0", "--port={GETH_PORT}", "--nodekey"={GETH_NODEKEY}]
"""

class Geth(TemplateBase):
    version = '0.0.2'
    template_name = 'geth'

    _DATA_DIR = '/mnt/data'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # bind uninstall action to the delete method
        self.add_delete_callback(self.uninstall)
        self._node_sal = j.clients.zos.get('local')
        self.__client_sal = None
    
        # Schedule a recurring action that checks if geth is synced and update state
        self.recurring_action(self._check_sync, 60)

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
            'GETH_NETWORK': str(self.data['network']),
            'GETH_VERBOSITY': str(self.data['verbosity']),
            'GETH_LIGHTSERV': str(self.data['lightserv']),
            'GETH_SYNCMODE': str(self.data['syncmode']),
            'GETH_NAT':  str(self.data['nat']),
            'GETH_V5DISC': str(self.data['v5disc']),
            'GETH_DATADIR': str(self.data['datadir']),
            'GETH_PORT': str(self.data['ethport']),
            'GETH_NODEKEY': str(self.data['nodekey']),
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
        vol = os.path.join(fs.path, self.guid)
        node_fs.mkdir(vol)

        mounts = [
            {
                'source': vol,
                'target': self._DATA_DIR
            }
        ]

        container_data = {
            'flist': self.data['gethFlist'],
            'mounts': mounts,
            'name': self._container_name,
        }

        container_data['ports'] = {
            str(self.data['ethport']): self.data['ethport'],
        }
        container_data['env'] = self._container_autostart_env

        self._container = self._node_sal.containers.create(**container_data)
        return self._container

    def install(self):
        """
        Creating geth container with the provided flist, and configure mounts for datadirs
            'flist': GETH_FLIST,
        """
        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)
    
        self.logger.info('installing geth %s', self.name)

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        """Remove the persistent volume of ethereum, and delete the
        container."""
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

    def start(self):
        """starts geth."""
        self.state.check('actions', 'install', 'ok')

        self._get_container()

        self.state.set('status', 'started', 'ok')
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """stop geth."""
        self.logger.info('Stopping geth %s', self.name)
        self._container_sal.stop()

        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def upgrade(self, gethFlist=None):
        """upgrade the container with an updated flist this is done by stopping
        the container and respawn again with the updated flist.

        gethFlist: If provided, the current used flist will be replaced with the specified one
        """
        # update flist
        if gethFlist:
            self.data['gethFlist'] = gethFlist

        self.stop()
        # restart geth in new container
        self.start()
    
    def run (self):
        """runs geth."""
        # Check if container is started
        self.state.check('actions', 'start', 'ok')

        self.check_empty_values_args()
    
        args = ["--rpc", "--{network}".format(**self.data), "--verbosity={verbosity}".format(**self.data),
        "--lightserv={lightserv}".format(**self.data), "--nat={nat}".format(**self.data), "--{v5disc}".format(**self.data), 
        "--syncmode={syncmode}".format(**self.data), "--datadir={datadir}".format(**self.data),
        "--rpcaddr=0.0.0.0", "--port={ethport}".format(**self.data), "--nodekey={nodekey}".format(**self.data)]

        container = self._node_sal.containers.get(self._container_name)

        if not container.client.filesystem.exists("/sandbox/bin/bootnode.key"):
            """
                Generate new bootnode key for this node if it does not exists
            """
            container.client.system("/sandbox/bin/bootnode -genkey /mnt/data/bootnode.key")

        start_cmd = "/sandbox/bin/geth {}".format(' '.join(map(str ,args)))

        # Start the geth node process with given args
        container.client.system(start_cmd)

        self.state.set('status', 'running', 'ok')
        self.state.set('actions', 'run', 'ok')
    
    def check_empty_values_args (self):
        if str(self.data['verbosity']) == "":
            self.data['verbosity'] = 4
        if str(self.data['lightserv']) == "":
            self.data['lightserv'] = 90
        if str(self.data['nat']) == "":
            self.data['nat'] = "none"
        if str(self.data['v5disc']) == "":
            self.data['v5disc'] = "v5disc"
        if str(self.data['syncmode']) == "":
            self.data['syncmode'] = "full"
        if str(self.data['ethport']) == "":
            self.data['ethport'] = 30303
        if str(self.data['nodekey']) == "":
            self.data['nodekey'] = "/sandbox/bin/bootnode.key"

    def get_enode_address(self):
        port=self.data['ethport']
        container = self._node_sal.containers.get(self._container_name)
        ip = str(container.default_ip().ip)
    
        enode_address = container.client.system("/sandbox/bin/bootnode -nodekey /mnt/data/bootnode.key -writeaddress").get().stdout
    
        enode="enode://{}@{}:{}".format(enode_address.strip("\n"), ip, port)
        return enode

    def get_args(self):
        args = ["--rpc", "--{network}".format(**self.data), "--verbosity={verbosity}".format(**self.data),
        "--lightserv={lightserv}".format(**self.data), "--nat={nat}".format(**self.data), "--{v5disc}".format(**self.data), 
        "--syncmode={syncmode}".format(**self.data), "--datadir={datadir}".format(**self.data),
        "--rpcaddr=0.0.0.0", "--port={ethport}".format(**self.data), "--nodekey={nodekey}".format(**self.data)]
        
        start_cmd = "/sandbox/bin/geth {}".format(' '.join(map(str ,args)))
        return start_cmd

    def _check_sync(self):
        """
        recurring function that updates service state with the ethereum syncing state every 60 seconds. ref init
        """
        result = self.get_syncing_status()
        if result is None:
            self.state.delete('ethereum','syncing')
            self.state.delete('ethereum','synced')
            return

        currentblock, highestblock = result
        if currentblock >= highestblock:
            self.state.set('ethereum','synced', 'ok')
            self.state.delete('ethereum','syncing')
        else:
            self.state.set('ethereum','syncing', 'ok')
            self.state.delete('ethereum','synced')

    def get_syncing_status(self):
        """
        fetches current and highest block from the ethereum node rpc
        Returns:
            *None - if geth is not syncing
            *[currentblock, highestblock] - if geth is syncing
        """
        random_id = str(uuid.uuid4())
        payload = {"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":random_id}
        headers = {"content-type": "application/json"}
        container = self._node_sal.containers.get(self._container_name)
        ip = str(container.default_ip().ip)
        r = requests.post(url="http://{}:8545".format(ip), data=j.data.serializer.json.dumps(payload), headers=headers)
        response = r.json()
    
        response_id = response["id"]
        jsonrpc = response["jsonrpc"]

        if response_id != random_id:
            raise InvalidResponseError(message="wrong response id", response=response)
        
        if jsonrpc != "2.0":
            raise InvalidResponseError(message="wrong json rpc version", response=response)

        result = response["result"]

        if not result:
            return None
        
        currentblock = int(result.get("currentBlock", "0x0"), 16)
        highestblock = int(result.get("highestBlock", "0x0"), 16)
        return currentblock, highestblock

class InvalidResponseError(Exception):
    """
    Invalid response error is returned when the jsonrpc response
    from ethereum node is invalid
    """
    def __init__(self, message, response):
        self._response = response
        super().__init__(message)

    @property
    def response(self):
        """
        Unexpeced response returned via ethereum node
        """
        return self._response
