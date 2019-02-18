import os
import pytest
import tempfile
import shutil
from unittest import mock, TestCase
from unittest.mock import MagicMock, patch, call
from zerorobot import config, template_collection
from zerorobot.template_uid import TemplateUID
from JumpscaleZrobot.test.utils import ZrobotBaseTest
from zerorobot.template.state import StateCheckError
from zerorobot import service_collection as scol
import gevent
from block_creator import BlockCreator


def mockdecorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


patch("zerorobot.template.decorator.timeout",
      MagicMock(return_value=mockdecorator)).start()
patch("zerorobot.template.decorator.retry",
      MagicMock(return_value=mockdecorator)).start()


class TestBlockCreatorTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), BlockCreator)
        cls.valid_data = {
            'node': 'local',
            'rpcPort': 23112,
            'apiPort': 23110,
            'walletSeed': '',
            'walletPassphrase': '',
            'walletAddr': '',
            'network': 'devnet',
            'tfchainFlist': 'https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-tfchain-autostart-master_faucetexplorerautobuild.flist'
        }

    def setUp(self):
        patch('jumpscale.j.clients.zos.get', MagicMock()).start()
        patch('jumpscale.j.sal_zos.tfchain.client', MagicMock()).start()
        patch("gevent.sleep", MagicMock()).start()
        patch("time.sleep", MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_valid_data(self):
        bc = BlockCreator(name='blockcreator', data=self.valid_data)
        assert bc.data == self.valid_data

    def test_node_sal(self):

        get_node = patch('jumpscale.j.clients.zos.get',
                         MagicMock(return_value='node')).start()
        bc = BlockCreator('bc', data=self.valid_data)
        node_sal = bc._node_sal
        assert get_node.called
        assert node_sal == 'node'

    def test_service_container_name(self):
        bc = BlockCreator('bc', data=self.valid_data)
        assert bc._container_name == "container-{}".format(bc.guid)
        # assert bc

    def test_client_sal(self):
        tfchain_client = patch('jumpscale.j.sal_zos.tfchain.client', MagicMock(
            return_value='client')).start()
        bc = BlockCreator('bc', data=self.valid_data)
        client_sal = bc._client_sal
        assert tfchain_client.called
        assert client_sal == 'client'

    def test_install(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._get_container = MagicMock()
        # bc._node_sal.storagepools.get.create = MagicMock(return_value=MagicMock())
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)

        bc.install()

        sp.get.assert_called_once()
        assert not sp.create.called
        assert bc.state.check('actions', 'install', 'ok')

    def test_install_with_value_error(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._get_container = MagicMock()
        sp = MagicMock()
        sp.get = MagicMock(side_effect=ValueError())
        sp.create = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs

        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.install()

        sp.create.assert_called_once()
        assert bc.state.check('actions', 'install', 'ok')

    def test__get_container_uninstalled(self):
        bc = BlockCreator('bc', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)

        bc._node_sal.client.filesystem = MagicMock()
        with pytest.raises(StateCheckError):
            bc._get_container()

            bc._node_sal.client.filesystem.mkdir.assert_has_calls([mock.call('mypath/wallet'),
                                                                   mock.call('mypath/backups')])

    def test__get_container(self):
        bc = BlockCreator('bc', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)

        bc._node_sal.client.filesystem = MagicMock()
        bc.state.set("actions", "install", "ok")
        bc._get_container()

        bc._node_sal.client.filesystem.mkdir.assert_has_calls([mock.call('mypath/wallet'),
                                                               mock.call('mypath/backups')])

    def test_start(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set('actions', 'install', 'ok')
        bc._get_container = MagicMock()
        bc._wallet_init = MagicMock()

        bc.start()
        bc._get_container.assert_called_once()
        bc._wallet_init.assert_called_once()
        bc.state.check('status', 'running', 'ok')
        bc.state.check('actions', 'start', 'ok')

    def test_start_not_install(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._get_container = MagicMock()
        bc._wallet_init = MagicMock()
        with pytest.raises(StateCheckError):
            bc.start()

    def test_stop(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set('actions', 'install', 'ok')
        bc.state.set('actions', 'start', 'ok')
        bc.state.set('status', 'running', 'ok')

        bc._container_sal.stop = MagicMock()
        bc.stop()

        bc._container_sal.stop.assert_called_once()

        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
            bc.state.check('actions', 'start', 'ok')
            bc.state.check('wallet', 'init', 'ok')

    def test_uninstall(self):
        bc = BlockCreator('bc', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.state.set("actions", "install", "ok")
        bc.uninstall()
        fs.delete.assert_called_once()

        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
            bc.state.check('actions', 'intsall', 'ok')

    def test_uninstall_with_value_error(self):
        bc = BlockCreator('bc', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        fs.side_effect = ValueError()
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.state.set("actions", "install", "ok")
        bc.uninstall()
        assert fs.delete.called
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
            bc.state.check('actions', 'intsall', 'ok')

    def test_upgrade(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.stop = MagicMock()
        bc.start = MagicMock()
        bc.upgrade("myflist")
        bc.stop.assert_called_once()
        bc.start.assert_called_once()
        assert bc.data['tfchainFlist'] == 'myflist'

    def test_wallet_init_unregistered_wallet_endpoint(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.stop = MagicMock()
        side_effects = [RuntimeError(), True]
        bc._client_sal.wallet_init = MagicMock(side_effect=side_effects)
        bc._client_sal.recovery_seed = "dmdm"
        bc._wallet_init()
        bc._client_sal.wallet_init.call_count == 2

    def test_wallet_init_first_time(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.stop = MagicMock()
        bc._client_sal.wallet_init = MagicMock()
        bc._client_sal.recovery_seed = "dmdm"

        bc._wallet_init()
        assert bc._client_sal.wallet_init.called
        assert bc.data['walletSeed'] == "dmdm"
        bc.state.check("wallet", "init", "ok")

    def test_wallet_init_already_initialized(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc._client_sal.wallet_init = MagicMock()
        bc._client_sal.recovery_seed = "dmdm"
        bc._wallet_init()
        assert not bc._client_sal.wallet_init.called

    def test_wallet_address_inited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc.state.set("status", "running", "ok")
        bc._client_sal.create_new_wallet_address = MagicMock(
            return_value='myaddr')
        bc.wallet_address()
        assert bc._client_sal.create_new_wallet_address.called
        assert bc.data['walletAddr'] == 'myaddr'

    def test_wallet_address_inited_wallet_configured_addr(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc.data['walletAddr'] = 'myaddrconfigured'
        bc._client_sal.create_new_wallet_address = MagicMock(
            return_value='myaddr')
        bc.wallet_address()
        assert not bc._client_sal.create_new_wallet_address.called
        assert bc.data['walletAddr'] == 'myaddrconfigured'

    def test_wallet_address_uninited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        with pytest.raises(StateCheckError):
            bc.wallet_address()

    def test_wallet_amount_inited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc.state.set("status", "running", "ok")
        bc._client_sal.wallet_amount = MagicMock(return_value='something')

        assert bc.wallet_amount() == 'something'

    def test_wallet_amount_uninited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._client_sal.wallet_amount = MagicMock(return_value='something')
        with pytest.raises(StateCheckError):
            bc.wallet_amount() == 'something'

    def test_consensus_stat_inited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc.state.set("status", "running", "ok")
        bc._client_sal.consensus_stat = MagicMock(return_value='something')

        assert bc.consensus_stat() == 'something'
        assert bc._client_sal.consensus_stat.called

    def test_consensus_stat_uninited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._client_sal.consensus_stat = MagicMock(return_value='something')

        with pytest.raises(StateCheckError):
            assert bc.consensus_stat() == 'something'
            assert bc._client_sal.consensus_stat.called

    def test_report_inited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc.state.set("wallet", "init", "ok")
        bc.state.set("status", "running", "ok")
        bc._client_sal.get_report = MagicMock(return_value={})

        assert isinstance(bc.report(), dict)
        bc._client_sal.get_report.assert_called_once()

    def test_report_uninited_wallet(self):
        bc = BlockCreator('bc', data=self.valid_data)
        bc._client_sal.get_report = MagicMock(return_value={})

        with pytest.raises(StateCheckError):
            bc.report()
