import os
import time
from random import shuffle

from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

from jinja2 import Template

CORE_FILE = Template("""
. {
    threebot {{zone}} {
        {% for explorer in explorers %}
        explorer {{explorer}}
        {% endfor %}
    }
    forward 8.8.8.8 9.9.9.9 
}

""")


class Coredns3bot(TemplateBase):
    version = '0.0.1'
    template_name = 'coredns3bot'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # bind uninstall action to the delete method
        self.add_delete_callback(self.uninstall)
        self._node_sal = j.clients.zos.get('local')

    def validate(self):
        self.state.delete('status', 'running')
        if not self.data['zone'].endswith("."):
            raise ValueError(
                'Invalid zone {} : needs to end with `.`'.format(self.data['zone']))

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
            'COREDNS_PORT': '%d' % self.data['dnsPort'],
        }

    def _get_container(self):
        """Create container object

        Returns:
            Container -- container the service is operating on.
        """
        self.state.check("actions", "install", "ok")

        container_data = {
            'flist': self.data['coredns3botFlist'],
            'name': self._container_name,
        }

        container_data['ports'] = {
            'udp|53': 53
        }
        container_data['env'] = self._container_autostart_env
        explorers = self.data['explorers']
        if len(explorers) != 0:
            container_data['config'] = {'/Corefile': self._get_corefile()}

        return self._node_sal.containers.create(**container_data)

    def install(self):
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        try:
            self._container_sal.stop()
        except Exception as e:
            self.logger.warning(
                "removing container on the uninstall {}".format(e))

        self.state.delete('actions', 'install')

    def upgrade(self, coredns3bot=None):
        """Upgrade the container with an updated coredns3bot flist this is done by
        stopping the container and respawn again with the updated flist.

        coredns3bot: If provided, the current used flist will be replaced with the specified one
        """
        # update flist
        if coredns3bot:
            self.data['coredns3bot'] = coredns3bot

        self.stop()
        self.start()

    def start(self):
        """
        Creating coredns3bot container with the provided flist
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

    def _get_corefile(self):
        return CORE_FILE.render(zone=self.data['zone'], explorers=self.data['explorers'])
