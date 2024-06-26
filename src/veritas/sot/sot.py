import yaml
from importlib import resources
from loguru import logger

# pynautobot
from pynautobot import api

# vertias packages
from veritas.sot import ipam
from veritas.sot import getter
from veritas.sot import selection
# from veritas.sot import onboarding
from veritas.sot import device as dvc
from veritas.sot import importer
from veritas.sot import updater
from veritas.sot import rest
from veritas.sot import job


class Sot:
    """
    A class to access nautobot, onboard devices, parse configs and many more

    This class is a 'wrapper' to implement the fluent syntax and to connect to nautobot.
    The real work is 'done' in the subpackage.

    Currently the following subpackages are available:
        - onboarding
        - ipam
        - get
        - importer
        - updater
        - job

    Parameter
    ----------
    url : `str`
        nautobot url
    token : str 
        token to access nautobot
    api_version: str
        API Version of nautobot
    ssl_verify : bool 
        check TLS

    Examples
    --------
    Init sot object

    >>> sot = sot.Sot(url="127.0.0.1:8008",
    >>>               token="12345",
    >>>               ssl_verify=alse)
    
    """

    def __init__(self, url, token, ssl_verify=True, api_version='2.0', debug=False) -> None:
        self._onboarding = None
        self._ipam = None
        self._getter = None
        self._selection = None
        self._importer = None
        self._nautobot = None
        self._updater = None
        self._job = None
        self._sot_config = {}

        if debug:
            logger.enable("veritas.sot")
            logger.enable("veritas.onboarding")
            logger.enable("veritas.inventory")
            logger.enable("veritas.profile")
        else:
            logger.disable("veritas.sot")
            logger.disable("veritas.onboarding")
            logger.disable("veritas.inventory")
            logger.disable("veritas.profile")

        logger.debug('reading SOT config')
        package = f'{__name__.split(".")[0]}.sot.data.sot'
        with resources.open_text(package, 'config.yaml') as f:
            self._sot_config = yaml.safe_load(f.read())

        self._sot_config['nautobot_url'] = url
        self._sot_config['nautobot_token'] = token
        self._sot_config['ssl_verify'] = ssl_verify
        self._sot_config['api_version'] = api_version

    def __getattr__(self, item):
        """return sub package

        Parameters
        ----------

        item : str
            name of subpackage

        Returns
        -------
        object
            the subpackage (init is called and object initialzed with parameter)

        Examples
        --------
        device = sot.get.device(name='my_device')

        """
        # if item == "onboarding":
        #     if self._onboarding is None:
        #         self._onboarding = onboarding.Onboarding(self)
        #     return self._onboarding
        if item == "ipam":
            if self._ipam is None:
                self._ipam = ipam.Ipam(self)
            return self._ipam
        if item == "get":
            if self._getter is None:
                self._getter = getter.Getter(self)
            return self._getter
        if item == "importer":
            if self._importer is None:
                self._importer = importer.Importer(self)
            return self._importer
        if item == "updater":
            if self._updater is None:
                self._updater = updater.Updater(self)
            return self._updater
        if item == "job":
            if self._job is None:
                self._job = job.Job(self)
            return self._job

    @property
    def nautobot_token(self) -> str:
        """returns token to access nautobot"""       
        return self._sot_config['nautobot_token']

    @property
    def ssl_verify(self) -> bool:
        """returns if ssl is verified or not"""
        return self._sot_config['ssl_verify']

    @property
    def nautobot_url(self) -> str:
        """returns nautobot url"""
        return self._sot_config['nautobot_url']

    @property
    def sot_config(self) -> dict:
        """returns sot config"""
        return self._sot_config

    def device(self, device) -> dvc:
        """initialize subpackage device and returns it

        Parameters
        ----------
        device : str
            name of device
       
        Returns
        -------
        device
            the corresponding device
        
        See Also
        --------

        Examples
        --------
        device = sot.device(name='lab.local')

        """
        return dvc.Device(self, device)

    def select(self, selected_values) -> selection:
        """returns initialized selection object to access nautobot

        Parameters
        ----------
        *unnamed
            unnamed parameter that are passed to the rest object

        Returns
        -------
        selection
            initialized selction object

        Examples
        --------
        devices = sot.select('id').using('nb.devices').where('name=lab.local')

        """
        return selection.Selection(self, selected_values)

    def rest(self, *unnamed, **named) -> rest:
        """returns initialized rest object to make REST api calls (requests)

        Parameters
        ----------
        *unnamed
            unnamed parameter that are passed to the rest object
        **named
            named parameter that are passed to the rest object
       
        Returns
        -------
        rest
            initialized rest object

        Raises
        ======
            None

        Examples
        --------
        rest = sot.rest(url='http://127.0.0.1', username='username', password='password')
        """
        return rest.Rest(self, *unnamed, **named)

    def open_nautobot(self) -> api:
        """opens connection to nautobot

        Parameters
        ----------
       
        Returns
        -------
        api
            connection to nautobot

        Raises
        ======
            None
        
        Examples
        --------
        >>> nautobot = sot.open_nautobot()
        """
        if self._nautobot is None:
            api_version = self._sot_config.get('api_version', '2.0')
            ssl_verify = self._sot_config['ssl_verify']
            logger.trace(f'url={self._sot_config["nautobot_url"]} token={self._sot_config["nautobot_token"]}')
            logger.debug(f'creating nautobot api object; api_version={api_version} ssl_verify={ssl_verify}')
            self._nautobot = api(url=self._sot_config['nautobot_url'], 
                                 token=self._sot_config['nautobot_token'], 
                                 api_version=api_version,
                                 verify=ssl_verify)
            self._nautobot.http_session.verify = ssl_verify

        return self._nautobot

    def enable_debug(self):
        """enabled logging of the veritas lib

        Examples
        --------
        sot.enable_debug()
        """
        logger.enable("veritas.sot")

