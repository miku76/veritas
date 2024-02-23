import yaml
import importlib
from ttp import ttp
from loguru import logger

# veritas
from veritas.onboarding import plugins
from veritas.configparser import abstract_configparser


class Configparser(abstract_configparser.Configparser):
    """configparser for Cisco devices

    Parameters
    ----------
    config : list
        device configuration
    platform : str
        platform of the device (ios, nxos, iosxr, asa, ...)
    """
    def __init__(self, config:list, platform:str='ios'):
        self._device_config = config
        self._parser = None
        self._template = None
        self._template_filename = None
        self._parsed_config = [{}]
        # naming is used to save the exact spelling of the interface
        # nxos and ios differs using Port-channel/Port-Channel/port-channel
        self._naming = {}

        package = f'{__name__.split(".")[0]}.configparser.data'
        with importlib.resources.open_text(package, 'config.yaml') as f:
            self._my_config = yaml.safe_load(f.read())

        if not self.parse(config, platform):
            logger.critical('failed to parse config')

    #
    # abstract methods (mandatory to implement)
    #

    def get_interface_ipaddress(self, interface:str) -> dict:
        """get interface IP address

        Parameters
        ----------
        interface : str
            name of the interface

        Returns
        -------
        interface : dict
            interface configuration
        """        
        return self._parsed_config[0].get('interfaces', {}).get(interface, {}).get('ip', None)

    def get_interface_name_by_address(self, address:str) -> str | None:
        """get interface name by IP address

        Parameters
        ----------
        address : str
            IP address

        Returns
        -------
        interface_name : str | None
            interface name
        """        
        interfaces = self._parsed_config[0].get('interfaces', {})
        ip = address.split('/')[0]
        for name, properties in interfaces.items():
            if ip == properties.get('ip'):
                logger.debug(f'found IP {ip} on {name}')
                return name
        return None

    def get_interfaces(self) -> dict:
        """get interfaces

        Returns
        -------
        interfaces : dict
            interfaces
        """        
        return self._parsed_config[0].get('interfaces', {})

    def find_in_global(self, properties:dict) -> bool:
        """check if properties are found in global config

        Parameters
        ----------
        properties : dict
            properties to search for

        Returns
        -------
        found : bool
            True if found, False otherwise
        """        
        key = None
        value = None

        for k,v in properties.items():
            if 'match' in k:
                key = k
                value = v
    
        global_config = self.get_global_config()

        # the key can be match__ic etc.
        cmd = key.split('__')[0]
        if '__' in key:
            lookup = key.split('__')[1]

        logger.debug(f'cmd: "{cmd}" lookup: "{lookup}" value: "{value}" lines: {len(global_config)}')

        for line in global_config:
            if properties.get('ignore_leading_spaces'):
                src = line.lstrip()
            else:
                src = line

            if self._find_in_line(cmd, lookup, value, src):
                logger.debug('found pattern in global config')
                return True
        
        return False

    def find_in_interfaces(self, properties:dict) -> list:
        """return list of interfaces that match properties

        Parameters
        ----------
        properties : dict
            properties to search for

        Returns
        -------
        interfaces : list
            list of interfaces that match properties
        """        
        key = None
        value = None
        ignore_leading_spaces = False

        for k,v in properties.items():
            if 'match' in k:
                key = k
                value = v
            elif 'ignore_leading_spaces' == k:
                ignore_leading_spaces = v
    
        interface_config = self.get_section('interfaces')

        # matched_on contains the list of all interfaces the value matched
        matched_on = []
        # the key can be match__ic etc.
        cmd = key.split('__')[0]
        if '__' in key:
            lookup = key.split('__')[1]

        logger.debug(f'cmd: "{cmd}" lookup: "{lookup}" value: "{value}" lines: {len(interface_config)}')

        for line in interface_config:
            if ignore_leading_spaces:
                src = line.lstrip()
            else:
                src = line

            if src.lower().startswith('interface '):
                interface = line[10:]
            
            if self._find_in_line(cmd, lookup, value, src):
                matched_on.append(interface)

        logger.debug(f'matched_on={matched_on}')
        return matched_on

    #
    # optional functions
    #

    def parse(self, config:list=None, platform:str='ios') -> bool:
        """parse configuration of device

        Parameters
        ----------
        config : list, optional
            device config, by default None
        platform : str, optional
            platform, by default 'ios'

        Returns
        -------
        parsed : bool
            true if parsing was successful, false otherwise
        """        
        # get template
        ttp_template = self._get_template(platform=platform)
        if not ttp_template:
            logger.debug('failed to get template; parsing aborted')
            return False

        device_config = config if config else self._device_config

        # create parser object and parse data using template:
        logger.debug('parsing device config')
        try:
            self._parser = ttp(data=device_config, 
                               template=ttp_template,
                               log_level="CRITICAL")
            self._parser.parse()
            self._parsed_config = self._parser.result(format='raw')[0]
            self._save_naming()
            return True
        except Exception as exc:
            logger.error(f'failed to parse config; got exception {exc}')
            return False

    def get_fqdn(self) -> str:
        """get FQDN of device

        Returns
        -------
        fqdn : str
            fqdn of device
        """        
        domain = self._parsed_config[0].get('global', {}).get('fqdn',{}).get('domain_name',"")
        hostname = self._parsed_config[0].get('global', {}).get('fqdn',{}).get('hostname')
        if domain:
            return f'{hostname}.{domain}'
        else:
            return hostname

    def get_interface(self, interface:str) -> dict | None:
        """get interface configuration by name

        Parameters
        ----------
        interface : str
            name of the interface

        Returns
        -------
        interface : dict | None
            interface configuration or None if not found
        """        
        return self._parsed_config[0].get('interfaces', {}).get(interface, None)

    def get_vlans(self) -> tuple[list, list, list]:
        """get vlans of the device

        Returns
        -------
        global_vlans, svi, trunk_vlans : tuple[list, list, list]
            global_vlans, svi, trunk_vlans
        """        
        global_vlans = []
        svi = []
        trunk_vlans = []

        for vid, properties in self._parsed_config[0].get('global',{}).get('vlan',{}).items():
            global_vlans.append({'vid': vid,
                                 'name': properties.get('name', 'unknown')})
    
        for name, properties in self._parsed_config[0].get('interfaces', {}).items():
            if 'vlan' in name.lower():
                svi.append({'vid': name[4:],
                            'name': properties.get('description','unkown')})
            if 'vlans_allowed' in properties:
                for vid in properties.get('vlans_allowed'):
                    trunk_vlans.append({'vid': vid,
                                        'name': 'trunked VLAN'})

        return global_vlans, svi, trunk_vlans

    def get_correct_naming(self, name:str) -> str:
        """return the right nameing of a port-channel

        nxos and ios uses differnet naming for port-channel
        ios uses Port-channel, nxos uses port-channel

        Parameters
        ----------
        name : str
            interface name

        Returns
        -------
        name : str
            either Port-channel or port-channel
        """        
        return self._naming.get(name.lower(), name)

    def get_device_config(self) -> list:
        """return (not parsed) device configuration

        Returns
        -------
        config : list
            configuration of the device
        """        
        return self._device_config

    def get_section(self, section:str) -> list:
        """return section of the device configuration by name

        Parameters
        ----------
        section : str
            name of the section

        Returns
        -------
        section : list
            section of the device configuration
        """        
        response = []
        if section == "interfaces":
            found = False
            for line in self._device_config.splitlines():
                # find first occurence of the word interface at the beginning of the line
                if line.lower().startswith('interface '):
                    found = True
                    response.append(line)
                    continue
                if found and line.startswith(' '):
                    response.append(line)
                else:
                    found = False
        else:
            for line in self._device_config.splitlines():
                # check if line begins with 'section'
                if line.lower().startswith(section):
                    response.append(line)

        return response

    def get_global_config(self) -> list:
        """return global configuration of the device

        Returns
        -------
        global_config : list
            global configuration of the device
        """        
        response = []
        for line in self._device_config.splitlines():
            if line.lower().startswith('interface '):
                found = True
                continue
            elif not line.lower().startswith('interface '):
                found = False
            if not found:
                response.append(line)

        return response

    #
    # internals
    #

    def _find_in_line(self, key, lookup, value, line):
        """
        n - not equal to (negation)
        ic - case-insensitive contains (*)
        c - case-sensitive contains (*)
        ie - case-insensitive exact match (*)

        nic - negated case-insensitive contains
        isw - case-insensitive starts-with
        nisw - negated case-insensitive starts-with
        iew - case-insensitive ends-with
        niew - negated case-insensitive ends-with
        nie - negated case-insensitive exact match
        re - case-sensitive regular expression match
        nre - negated case-sensitive regular expression match
        ire - case-insensitive regular expression match
        nire - negated case-insensitive regular expression match
        """

        # logger.debug(f'key: {key} lookup: {lookup} value: {value} line: {line}')
        if key == 'match':
            if lookup == "ie":
                # case-insensitive exact match
                if line.lower() == value.lower():
                    return True
            elif lookup == "ic":
                # case-insensitive contains
                if value.lower() in line.lower():
                    return True
            elif lookup == "c":
            # case-sensitive contains
                if value in line:
                    return True
            else:
                if line == value:
                    return True

        return False

    def _save_naming(self):
        for interface in self._parsed_config[0].get('interfaces', {}):
            if 'Port-channel' in interface:
                self._naming["port-channel"] = "Port-channel"
            if 'port-channel' in interface:
                self._naming["port-channel"] = "port-channel"

    def _get_template(self, platform='ios'):
        if self._template is not None:
            return self._template

        if self._template_filename is None:
            # use default template that is configured in config
            filename = self._my_config.get('templates',{}).get(platform, None)
            logger.debug(f'using ttp template {filename}')
        else:
            filename = self._template_filename
        if filename is None:
            logger.error(f'please configure correct template filename for {platform}')
            return None

        package = f'{__name__.split(".")[0]}.configparser.data.templates'
        file = importlib.resources.files(package).joinpath(filename)
        short_file = str(file).rsplit("/")[-1]
        try:
            logger.debug(f'reading template {short_file}')
            with open(file) as f:
                ttp_template = f.read()
        except Exception as exc:
            logger.error(f'could not read template {file}; got exception {exc}')
            return None
        
        return ttp_template

@plugins.configparser('ios')
def get_configparser(config, platform):
    return Configparser(config=config, platform=platform)
