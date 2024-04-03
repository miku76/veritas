from loguru import logger
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core import Nornir


# veritas
from veritas.inventory import veritasinventory
from veritas.tools import tools
from veritas.sot import sot as veritas_sot


class Job(object):
    """This class starts a job on the network. It uses nornir to run tasks on the network devices.

    Parameters
    ----------
    sot : veritas_sot
        the sot object to use to query the source of truth
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
    def __init__(self, sot:veritas_sot, result:str='raw', username:str=None, 
                 password:str=None, port:int=22, data:dict={}, select=[], defaults={}, 
                 groups={}, use_primary:bool=True, logging:dict={"enabled": False}):

        # we use the veritas inventory plugin
        InventoryPluginRegister.register("veritas-inventory", veritasinventory.VeritasInventory)

        self._sot = sot
        self._nornir = None
        self._nautobot = None
        self._on = None
        self._profile = None
        self._host_groups = []
        self._groups = groups
        self._result = result
        self._username = username
        self._password = password
        self._port = port
        self._data = data
        self._select = select
        self._use_primary = use_primary
        self._defaults = defaults
        self._logging = logging

    def on(self, *unnamed:list, **named:dict) -> None:
        """on sets the where clause to query the source of truth

        this method is used as fluent interface

        Parameters
        ----------
        unnamed : list
            list of unnamed arguments
        named : dict
            dictionary of named arguments

        the parameter are used as 'select' parameter to query the source of truth

        """        
        self._on = tools.convert_arguments_to_properties(unnamed, named)
        return self

    def set(self, profile=None, username=None, password=None, result=None, parse=False,
            port=None, plaintext:bool=False, use_primary=None, logging=None) -> None:
        """set is used to set the properties of the job

        this method is used as fluent interface

        Returns
        -------
        self
            the job object
        """
        self._profile = profile
        if self._profile:
            self._username = self._profile.username
            self._password = self._profile.password
        self._username = username if username else self._username
        self._password = password if password else self._password
        self._result = result if result else self._result
        self._parse_result = parse
        self._port = port if port else self._port
        self._cfg_plain_text = plaintext
        self._use_primary = use_primary if use_primary else self._use_primary
        self._logging = logging if logging else self._logging
        return self

    def init_nornir(self, data:dict=None, select:str=None, host_groups:list=[], groups:dict=None,
                     defaults={}, connection_options:dict=None, num_workers:int=10) -> Nornir:
        """init nornir

        Parameters
        ----------
        data : dict, optional
            additional data added to each host, by default None
        select : str, optional
            select variables; which values the user wants to get, by default None
        host_groups : list, optional
            list of group the host belongs to, by default []
        groups : dict, optional
            dict containing groups data, by default None
        defaults : dict, optional
            dict containing default values, by default {}
        connection_options : dict, optional
            dict of connection options, by default None
        num_workers : int, optional
            number of nornir workers, by default 10
        
        Notes
        -----
        The format to use connection_options is:
        {'napalm': {
          'extra': {
            'optional_args': {
              'conn_timeout':60,
            }
          }
         },
         'netmiko': {
           'extra': {
             'conn_timeout': 5,
             'auth_timeout': None,  # Timeout to wait for authentication response
             'banner_timeout': 15,  # Timeout to wait for the banner to be presented (post TCP-connect)
             'blocking_timeout':20, # Read blocking timeout
             'timeout':100,         # TCP connect timeout | overloaded to read-loop timeout
             'session_timeout': 60  # Used for locking/sharing the connection
           }
         }
        }
        """
        _data = data if data else self._data
        _select = select if select else self._select
        _host_groups = host_groups if len(host_groups) > 0 else self._host_groups
        _groups = groups if groups else self._groups
        _worker = num_workers
        _defaults = defaults if defaults else self._defaults

        # the inventory needs a list
        if isinstance(_select, str):
            _select = _select.replace(' ','').split(',')

        connection_opts = {
            'default': {
                'username': self._username,
                'password': self._password,
                'port': self._port
            }
        }
        if connection_options:
            connection_opts.update(connection_options)
            logger.bind(extra="nornir").debug(f'connection options: {connection_opts}')

        self._nornir = InitNornir(
            runner={
                "plugin": "threaded",
                "options": {
                    "num_workers": _worker,
                },
            },
            inventory={
                'plugin': 'veritas-inventory',
                # the next parameters are used by the veritas inventory plugin (init method)
                "options": {
                    'sot': self._sot,
                    'where': self._on,
                    'use_primary_ip': self._use_primary,
                    'username': self._username,
                    'password': self._password,
                    'connection_options': connection_opts,
                    'data': _data,
                    'select': _select,
                    'host_groups': _host_groups,
                    'defaults': _defaults,
                    'groups': _groups,
                }
            },
            logging=self._logging
        )
        return self._nornir
