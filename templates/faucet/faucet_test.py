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
from faucet import Faucet


def mockdecorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


patch("zerorobot.template.decorator.timeout",
      MagicMock(return_value=mockdecorator)).start()
patch("zerorobot.template.decorator.retry",
      MagicMock(return_value=mockdecorator)).start()


class TestFaucetTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Faucet)
        cls.valid_data = {
            'node': 'local',
            'rpcPort': 23112,
            'apiPort': 23110,
            'domain': 'coolcoin',
            'network': 'devnet',
            'ethPort': 3003,
            'faucetFlist': "https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-faucet-autostart-master_faucetexplorerautobuild.flist",
            'walletSeed': '',
            'walletPassphrase': '',
            'walletAddr': '',
            'faucetPort': 8080,
        }

    def setUp(self):
        patch('jumpscale.j.clients.zos.get', MagicMock()).start()
        patch('jumpscale.j.sal_zos.tfchain.client', MagicMock()).start()
        patch("gevent.sleep", MagicMock()).start()
        patch("time.sleep", MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_valid_data(self):
        bc = Faucet(name='f', data=self.valid_data)
        assert bc.data == self.valid_data

    def test_node_sal(self):

        get_node = patch('jumpscale.j.clients.zos.get',
                         MagicMock(return_value='node')).start()
        bc = Faucet('f', data=self.valid_data)
        node_sal = bc._node_sal
        assert get_node.called
        assert node_sal == 'node'

    def test_service_container_name(self):
        bc = Faucet('f', data=self.valid_data)
        assert bc._container_name == "container-{}".format(bc.guid)

    def test_blockcreator_service_name(self):
        bc = Faucet('f', data=self.valid_data)
        assert bc._block_creator_name == "block_creator-{}".format(bc.guid)

    def test_install(self):
        bc = Faucet('f', data=self.valid_data)
        # sp = MagicMock()
        # fs = MagicMock()
        # fs.path = 'mypath'
        # sp.get.return_value = fs
        # bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.api = MagicMock()

        waitf = MagicMock()
        bc._block_creator.schedule_action = MagicMock(return_value=waitf)

        bc.install()

        assert bc.api.services.find_or_create.called
        bc._block_creator.schedule_action.assert_called_once_with("install")
        # FIXME CHECK FOR WAITF
        # assert waitf.called

        bc.state.check('actions', 'install', 'ok')

    def test_install_with_value_error(self):
        bc = Faucet('f', data=self.valid_data)

        bc.api = MagicMock()

        bc._create_blockcreator = MagicMock(side_effect=RuntimeError())
        bc._block_creator.schedule_action = MagicMock()

        # TODO: better execption catching.
        with pytest.raises(Exception):
            bc.install()
            bc.state.check('actions', 'install', 'ok')

    def test__get_container_not_installed(self):
        bc = Faucet('f', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.api = MagicMock()
        bc._node_sal.client.filesystem = MagicMock()

        bc._get_caddyfile = MagicMock()
        bc._write_caddyfile = MagicMock()

        with pytest.raises(StateCheckError):
            bc._get_container()

            bc._node_sal.client.filesystem.mkdir.assert_has_calls([mock.call('mypath/wallet'),
                                                                   mock.call('mypath/caddy-certs')])

            assert bc._node_sal.containers.create.called
            assert bc._get_caddyfile.called

    def test__get_container_installed(self):
        bc = Faucet('f', data=self.valid_data)
        bc.state.set("actions", "install", "ok")

        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc.api = MagicMock()
        bc._node_sal.client.filesystem = MagicMock()

        bc._get_caddyfile = MagicMock()
        bc._write_caddyfile = MagicMock()

        bc._get_container()

        bc._node_sal.client.filesystem.mkdir.assert_has_calls([mock.call('mypath/wallet'),
                                                               mock.call('mypath/caddy-certs')])

        assert bc._node_sal.containers.create.called
        assert bc._get_caddyfile.called

    def test_start(self):
        bc = Faucet('f', data=self.valid_data)
        bc.state.set('actions', 'install', 'ok')
        bc._get_container = MagicMock()
        bc.api = MagicMock()
        bc._block_creator.schedule_action = MagicMock()
        bc.write_caddyfile = MagicMock()

        bc.start()

        bc._get_container.assert_called_once()
        assert bc.write_caddyfile.called

        bc.state.check('status', 'running', 'ok')
        bc.state.check('actions', 'start', 'ok')

    def test_start_not_install(self):
        bc = Faucet('f', data=self.valid_data)
        bc._get_container = MagicMock()
        bc.api = MagicMock()
        bc._block_creator.schedule_action = MagicMock()
        bc._write_caddyfile = MagicMock()

        with pytest.raises(StateCheckError):
            bc.start()

    def test_stop(self):
        bc = Faucet('f', data=self.valid_data)
        bc.state.set('actions', 'start', 'ok')
        bc.state.set('status', 'running', 'ok')

        bc.api = MagicMock()
        bc._container_sal.stop = MagicMock()
        bc._block_creator.schedule_action = MagicMock()

        bc.stop()

        bc._container_sal.stop.assert_called_once()
        bc._block_creator.schedule_action.assert_called_once_with("stop")

        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
            bc.state.check('actions', 'start', 'ok')

    def test_uninstall(self):
        bc = Faucet('f', data=self.valid_data)
        sp = MagicMock()
        fs = MagicMock()
        fs.path = 'mypath'
        sp.get.return_value = fs
        bc.api = MagicMock()
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        bc._block_creator.schedule_action = MagicMock()
        bc.state.set("actions", "install", "ok")
        bc.uninstall()
        fs.delete.assert_called_once()

        bc._block_creator.schedule_action.assert_called_once()

        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
            bc.state.check('actions', 'intsall', 'ok')

    def test_uninstall_with_value_error(self):
        bc = Faucet('f', data=self.valid_data)
        bc.api = MagicMock()
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
        bc = Faucet('f', data=self.valid_data)
        bc.stop = MagicMock()
        bc.start = MagicMock()
        bc.upgrade("myflist")
        bc.stop.assert_called_once()
        bc.start.assert_called_once()
        assert bc.data['faucetFlist'] == 'myflist'
