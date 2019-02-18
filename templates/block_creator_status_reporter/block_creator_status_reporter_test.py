import os
import pytest
import tempfile
import shutil
from unittest import mock, TestCase
from unittest.mock import MagicMock, patch, call
from zerorobot import config, template_collection
from zerorobot.template_uid import TemplateUID
from JumpscaleZrobot.test.utils import ZrobotBaseTest, mock_decorator, task_mock
from zerorobot.template.state import StateCheckError
from zerorobot import service_collection as scol
import gevent
import requests
from block_creator_status_reporter import BlockCreatorStatusReporter


patch("zerorobot.template.decorator.timeout",
      MagicMock(return_value=mock_decorator)).start()
patch("zerorobot.template.decorator.retry",
      MagicMock(return_value=mock_decorator)).start()

BLOCK_CREATOR_TEMPLATE_UID = 'github.com/threefoldtoken/0-templates/block_creator/0.0.2'
NODE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node/0.0.1'


BlockCreatorStatusReporter.recurring_action = MagicMock()
requests_request = MagicMock()


class TestBlockCreatorStatusReporterTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), BlockCreatorStatusReporter)
        cls.valid_data = {
            'node': 'local',
            'blockCreator': 'blockcreator1',
            'blockCreatorIdentifier': '5',
            'postUrlTemplate': 'http://127.0.0.1:4567/blockcreators/{block_creator_identifier}/'
        }

    def setUp(self):
        patch('jumpscale.j.clients.zos.get', MagicMock()).start()
        patch('jumpscale.j.sal_zos.tfchain.client', MagicMock()).start()
        patch("gevent.sleep", MagicMock()).start()
        patch("time.sleep", MagicMock()).start()
        patch("requests.request", requests_request).start()

    def tearDown(self):
        patch.stopall()

    def test_create_valid_data(self):
        bc = BlockCreatorStatusReporter(
            name='blockcreator', data=self.valid_data)
        assert bc.data == self.valid_data

    def test_get__node(self):

        get_node = patch('jumpscale.j.clients.zos.get',
                         MagicMock(return_value='node')).start()
        bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
        bc.api = MagicMock()
        bc._node

        bc.api.services.get.assert_called_once_with(
            template_uid=NODE_TEMPLATE_UID, name='local')

    def test_get__blockcreator(self):

        bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
        bc.api = MagicMock()
        bc._block_creator
        bc.api.services.get.assert_called_once_with(
            template_uid=BLOCK_CREATOR_TEMPLATE_UID, name=bc.data['blockCreator'])

    def test_start(self):
        bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
        bc.start()
        bc.state.check('status', 'running', 'ok')

    def test_stop(self):
        bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
        bc.state.set('status', 'running', 'ok')
        bc.stop()

        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')

    def test_monitoring_not_running(self):
        bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
        bc.api = MagicMock()
        bc.state = MagicMock()
        bc._monitor()
        bc.state.check.assert_called_with("status", "running", "ok")

    # @pytest.mark.skip(reason="something wrong with task mocking")
    # def test_monitoring_running(self):
    #     bc = BlockCreatorStatusReporter('bc', data=self.valid_data)
    #     bc.api = MagicMock()

    #     report_task = task_mock({'data': 1})

    #     info_task = task_mock({'data': 'value'})
    #     stats_task = task_mock({
    #         'statkind1': {'history': {'300': 1}},
    #         'statkind2': {'history': {'300': 1}},
    #         'statkind3': {'history': {'300': 1}},
    #     })

    #     def sched_act(name):
    #         if name == "info":
    #             return info_task
    #         elif name == "stats":
    #             return stats_task
    #         else:
    #             raise ValueError("invalid action")

    #     bc._node.schedule_action = sched_act
    #     bc._block_creator.schedule_action = MagicMock(return_value=report_task)

    #     bc._monitor()

    #     assert requests_request.called
    #     assert report_task.wait.called
    #     assert info_task.wait.called
    #     assert stats_task.wait.called
