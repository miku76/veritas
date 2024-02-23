import os
import sys
import textfsm
from loguru import logger
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir_napalm.plugins.tasks import napalm_get, napalm_ping
from nornir_scrapli.tasks import (
    send_command,
    send_commands,
    send_configs
)

# veritas
from veritas.inventory import veritasinventory
from veritas.tools import tools


class Job(object):
    """This class starts a job on the network. It uses nornir to run tasks on the network devices.

    Parameters
    ----------
    result : str
       format of the result
    username : str
         username for the devices
    password : str
        password for the devices
    port : int
        port to connect to
    data : dict
        data to be added to the inventory
    use_primary : bool
        use primary ip address
    logging : dict
        logging settings
    """
    def __init__(self, sot, result:str='raw', username:str=None, password:str=None, port:int=22, data:dict={}, 
                 use_primary:bool=True, logging:dict={"enabled": False}):
        
        # we use the veritas inventory plugin
        InventoryPluginRegister.register("veritas-inventory", veritasinventory.VeritasInventory)

        self._sot = sot
        self._nornir = None
        self._nautobot = None
        self._on = None
        self._profile = None
        self._host_groups = []
        self._groups = {}
        self._result = result
        self._username = username
        self._password = password
        self._port = port
        self._data = data
        self._user_primary = use_primary
        self._logging = logging

    def init_nornir(self, *unnamed, **named):
        # returns the nornir object so that the user can 
        # run its own tasks
        properties = tools.convert_arguments_to_properties(unnamed, named)
        if not self._nornir:
            self._init_nornir(properties)
        return self._nornir 

    def __getattr__(self, item):
        if item.startswith('get_'):
            return self._getter(item)
        elif 'is_alive' == item:
            return self._direct(item)
        else:
            raise AttributeError ('unknown attribute')

    def on(self, *unnamed, **named):
        self._on = tools.convert_arguments_to_properties(unnamed, named)
        return self

    def set(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        self._profile = properties.get('profile')
        if self._profile:
            self._username = self._profile.username
            self._password = self._profile.password
        self._username = properties.get('username') if properties.get('username') else self._username
        self._password = properties.get('password') if properties.get('password') else self._password
        self._result = properties.get('result', self._result)
        self._parse_result = properties.get('parse', False)
        self._port = properties.get('port', self._port)
        self._cfg_plain_text = properties.get('plaintext', True)
        self._user_primary = properties.get('use_primary', self._user_primary)
        self._logging = properties.get('logger', self._logging)
        return self

    def add_data(self, *unnamed, **named):
        # we expect a list and add this list to our inventory data later
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self._data = [properties] if isinstance(properties, str) else properties
        return self

    def add_group(self, *unnamed, **named):
        # we expect a dict
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self._groups = properties
        return self

    def add_to_group(self, *unnamed, **named):
        # we expect a list
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self._host_groups = [properties] if isinstance(properties, str) else properties
        return self

    def ping(self,  *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        destination = properties.get('destination')
        count = properties.get('count',3)

        logger.info(f'ping {destination} {count}')
        self._init_nornir()
        result = self._nornir.run(name="ping", 
                                  task=napalm_ping, 
                                  dest=destination,
                                  count=count)
        return self._return(result)

    def get_config(self, *unnamed, **named):

        # get properties
        properties = tools.convert_arguments_to_properties(unnamed, named)
        config = properties if len(properties) > 0 else "running"
        logger.debug(f'getting {config} config')

        # init nornir
        self._init_nornir()
        result = self._nornir.run(
            name="get_config", task=napalm_get, getters=['config'], retrieve=config
        )
        return self._return(result)

    def send_configs(self, commands):

        logger.debug(f'send config {commands}')
        self._init_nornir()
        result = self._nornir.run(
            name="send_configs", task=send_configs, configs=commands
        )
        return self._return(result)

    def send_command(self, command):

        logger.debug(f'send command {command}')
        self._init_nornir()
        result = self._nornir.run(
            name=command, task=send_command, command=command
        )
        return self._return(result)

    def send_commands(self, commands):

        logger.debug(f'send commands {commands}')
        self._init_nornir()
        result = self._nornir.run(
            name="Send commands", task=send_commands, commands=commands
        )
        return self._return(result)

    # -------- internal methods --------

    def _init_nornir(self, data=None, host_groups=None, groups=None, logger=None, num_workers=100):

        if self._nornir is not None:
            return 

        _data = data if data else self._data
        _host_groups = host_groups if host_groups else self._host_groups
        _groups = groups if groups else self._groups
        _logger = logger if logger else self._logging
        _worker = num_workers

        self._nornir = InitNornir(
            runner={
                "plugin": "threaded",
                "options": {
                    "num_workers": _worker,
                },
            },
            inventory={
                'plugin': 'veritas-inventory',
                "options": {
                    'url': self._sot.nautobot_url,
                    'ssl_verify': self._sot.ssl_verify,
                    'token': self._sot.nautobot_token,
                    'query': self._on,
                    'use_primary_ip': self._user_primary,
                    'username': self._username,
                    'password': self._password,
                    'connection_options': {'default': {'username': self._username,
                                                       'password': self._password,
                                                       'port': self._port}
                                        },
                    'data': _data,
                    'host_groups': _host_groups,
                    'groups': _groups
                },
            },
            logging=self._logging,
        )

    def _getter(self, getter):

        logger.info(f'getter {getter}')
        self._init_nornir()
        result = self._nornir.run(name=getter, task=napalm_get, getters=getter)
        return self._return(result)

    def _direct(self, service):

        logger.info('is alive')
        self._init_nornir()
        if 'is_alive' == service:
            task = self._is_alive

        result = self._nornir.run(name=service, task=task)
        return self._return(result)

    def _is_alive(self, task):
        napalm = task.host.get_connection("napalm", task.nornir.config)
        return napalm.is_alive()

    def _normalize_result(self, results):
        response = {}

        for hostname in results:
            if hostname not in response:
                response[hostname] = {}
            result = results[hostname].result
            command = results[hostname].name.replace(' ','_')
            response[hostname][command] = result
        
        return response

    def _return(self, result):

        if self._parse_result:
            return self._parse_result(result)
        elif 'normalize' == self._result:
            return self._normalize_result(result)
        else:
            return result

    def _parse_result(self, results):
        BASEDIR = os.path.abspath(os.path.dirname(__file__))
        template_directory = os.path.join(BASEDIR, '../textfsm')
        response = {}
        for hostname in results:
            if hostname not in response:
                response[hostname] = {}
            host = self._nornir.inventory.hosts[hostname]
            platform = host.get('platform','ios')
            manufacturer = host.get('manufacturer','cisco')
            result = results[hostname].result
            command = results[hostname].name.replace(' ','_')
            filename = f'{manufacturer}_{platform}_{command}.textfsm'
            logger.info(f'result of {hostname} manufacturer: {manufacturer} platform {platform}')
            logger.info(f'using template {filename}')

            if command == "get_config":
                # it is either a startup or a running config
                if len(result.get('config').get('running')) > 0:
                    if self._cfg_plain_text and len(results) == 2:
                        # one host / user wants just the config
                        return result.get('config').get('running')
                    response[hostname][command] = result.get('config').get('running')
                elif len(result.get('config').get('startup')) > 0:
                    if self._cfg_plain_text and len(results) == 2:
                        # one host / user wants just the config
                        return result.get('config').get('startup')
                    response[hostname][command] = result.get('config').get('startup')
                else:
                    response[hostname][command] = result
                continue

            # check if template exists
            if not os.path.isfile("%s/%s" % (template_directory, filename)):
                logger.error("template %s does not exists" % filename)
                return results
            # now parse result using this template
            try:
                template = open("%s/%s" % (template_directory, filename))
                re_table = textfsm.TextFSM(template)
                fsm_results = re_table.ParseText(result)
                collection_of_results = [dict(zip(re_table.header, pr)) for pr in fsm_results]
                response[hostname][command] = collection_of_results
            except Exception as exc:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("parser error in line %s; got: %s (%s, %s, %s)" % (exc_tb.tb_lineno,
                                                                                 exc,
                                                                                 exc_type,
                                                                                 exc_obj,
                                                                                 exc_tb))
                response[hostname][command] = {}

        return response
