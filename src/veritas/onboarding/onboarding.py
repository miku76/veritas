import os
import yaml
import sys
import json
import socket
import csv
from os import path
from loguru import logger
from benedict import benedict
from deepmerge import always_merger

# veritas
import veritas.repo
from veritas.configparser import configparser as cfgparser
from veritas.sot import sot
from veritas.tools import tools
from veritas.devicemanagement import scrapli as dm
from veritas.onboarding.devices import get_device_properties as _get_device_properties
from veritas.onboarding.interfaces import get_vlan_properties as _get_vlan_properties
from veritas.onboarding.interfaces import get_interface_properties as _get_interface_properties
from veritas.onboarding.interfaces import get_primary_interface_by_address as _get_primary_interface_by_address
from veritas.onboarding.tags import get_tag_properties as _get_tag_properties


class Onboarding():

    def __init__(self, profile=None, username=None, password=None, 
                 config_filename=None, profile_filename='profiles.yaml'):

        self._all_defaults = None
        self._configparser = None
        self._device_config = None
        self._device_facts = None
        self._device_defaults = None
        self._device_properties = None
        self._profile_name = profile
        self._username = username
        self._password = password

        # read onboarding config
        main = path.abspath(str(sys.modules['__main__']))
        basedir = main.rsplit('/', 1)[0]
        self._onboarding_config = tools.get_miniapp_config('onboarding', basedir, config_filename)

        # load profiles
        profile_config = tools.get_miniapp_config('onboarding', basedir, profile_filename) if profile \
            else None

        # we need the SOT object to talk to it
        self._sot = sot.Sot(token=self._onboarding_config['sot']['token'],
                            ssl_verify=self._onboarding_config['sot'].get('ssl_verify', False),
                            url=self._onboarding_config['sot']['nautobot'])

        # get username and password either from profile or from the args
        logger.debug(f'getting profile profile={profile} username={username}')
        self._username, self._password = tools.get_username_and_password(
                                                profile_config,
                                                profile,
                                                username, 
                                                password)

    def parse_config(self, device_config, device_facts, device_defaults):
        """parse config and save device_config, device_facst and device_defaults for later use"""
        self._device_config = device_config
        self._device_facts = device_facts
        self._device_defaults = device_defaults

        # parse config / configparser is a dict that contains all necessary data
        self._configparser = cfgparser.Configparser(config=device_config, 
                                                    platform=device_defaults.get('platform','ios'))

        return self._configparser

    def get_onboarding_config(self):
        return self._onboarding_config

    def get_ip_from_host(self, host_or_ip):
        """return IP address of host"""
        try:
            # maybe the user has set a hostname instead of an address
            return socket.gethostbyname(host_or_ip)
        except Exception:
            return None

    def read_inventory(self, inventory):
        """read inventrory from file"""

        # check if file exists
        if not os.path.exists(inventory):
            logger.error('inventory does not exists or cannot be read')
            return benedict(keyattr_dynamic=True)

        logger.debug(f'reading inventory {inventory}')
        if 'csv' in inventory:
            return self.read_csv_inventory(inventory)
        elif 'yaml' in inventory or 'yml' in inventory:
            return self.read_yaml_inventory(inventory)
        elif 'xlsx' in inventory:
            return self.read_xlsx_inventory(inventory)
        else:
            logger.ciritical(f'unknown file format {inventory}')
            return benedict(keyattr_dynamic=True)

    def read_mapping(self):
        """read mapping from miniapps config"""
        conf_dir = self._onboarding_config.get('git').get('app_configs').get('path')
        directory = os.path.join(conf_dir, './onboarding/mappings/')

        filename = "%s/%s" % (directory, 
            self._onboarding_config.get('onboarding',{}).get('mappings',{}).get('inventory',{}).get('filename')
        )
        if filename:
            # read mapping from file
            logger.debug(f'reading mapping config {filename.rsplit("/")[-1]}')
            with open(filename) as f:
                mapping_config = yaml.safe_load(f.read())
            column_mapping = mapping_config.get('mappings',{}).get('columns',{})
            value_mapping = mapping_config.get('mappings',{}).get('values',{})

        return column_mapping, value_mapping

    def read_xlsx_inventory(self, inventory):
        """read inventory from xlsx file and build list"""

        devicelist = []

        # get mapping
        column_mapping, value_mapping = self.read_mapping()

        table = tools.read_excel_file(inventory)
        for row in table:
            device = benedict(keyattr_dynamic=True)
            for k,v in row.items():
                key = column_mapping.get(k) if k in column_mapping else k
                if key in value_mapping:
                    if v is None:
                        value = value_mapping[key].get('None', v)
                    else:
                        value = value_mapping[key].get(v, v)
                else:
                    value = v
                # convert 'true' or 'false' to boolean values
                if isinstance(value, str) and value.lower() == 'true':
                    value = True
                if isinstance(value, str) and value.lower() == 'false':
                    value = False
                device[key] = value
            devicelist.append(device)

        return devicelist

    def read_csv_inventory(self, inventory):
        """read inventory from csv file and build list"""

        devicelist = []

        # get mapping
        column_mapping, value_mapping = self.read_mapping()

        # set default values
        quote_config = self._onboarding_config.get('onboarding', {}).get('inventory', {}).get('csv')
        delimiter = quote_config.get('delimiter',',')
        quotechar = quote_config.get('quotechar','|')
        quoting_cf = quote_config.get('quoting','minimal')
        newline = quote_config.get('newline','')
        if quoting_cf == "none":
            quoting = csv.QUOTE_NONE
        elif quoting_cf == "all":
            quoting = csv.QUOTE_ALL
        elif quoting_cf == "nonnumeric":
            quoting = csv.QUOTE_NONNUMERIC
        else:
            quoting = csv.QUOTE_MINIMAL

        # read CSV file
        with open(inventory, newline=newline) as csvfile:
            csvreader = csv.DictReader(csvfile, delimiter=delimiter, quoting=quoting, quotechar=quotechar)
            for row in csvreader:
                device = benedict(keyattr_dynamic=True)
                for k,v in row.items():
                    key = column_mapping.get(k) if k in column_mapping else k
                    if key in value_mapping:
                        if v is None:
                            value = value_mapping[key].get('None', v)
                        else:
                            value = value_mapping[key].get(v, v)
                    else:
                        value = v
                    # convert 'true' or 'false' to boolean values
                    if isinstance(value, str) and value.lower() == 'true':
                        value = True
                    if isinstance(value, str) and value.lower() == 'false':
                        value = False
                    device[key] = value
                devicelist.append(device)

        return devicelist

    def read_yaml_inventory(self, inventory):
        """read inventory from yaml file and build list"""
        devicelist = []

        # get mapping
        column_mapping, value_mapping = self.read_mapping()

        with open(inventory) as f:
            try:
                table = yaml.safe_load(f.read())
            except Exception as exc:
                logger.error(f'could not read or parse config; got execption {exc}')
                return []

        for row in table.get('inventory', []):
            d = {}
            for k,v in row.items():
                key = column_mapping.get(k) if k in column_mapping else k
                if key in value_mapping:
                    if v is None:
                        value = value_mapping[key].get('None', v)
                    else:
                        value = value_mapping[key].get(v, v)
                else:
                    value = v
                # convert 'true' or 'false' to boolean values
                if isinstance(value, str) and value.lower() == 'true':
                    value = True
                if isinstance(value, str) and value.lower() == 'false':
                    value = False
                d[key] = value
            devicelist.append(d)

        return devicelist

    def get_device_defaults_from_prefix(self, all_defaults, ip):
        """
        the function returns the default values of a device
        we use the prefix path and merge all values that are on the path
        0.0.0.0/0 should always exists and contain the default values like the location
        or the default-role 
        If you do not use default values the onboarding process can faile because of missing but
        required values 
        """
        if all_defaults is None:
            return benedict(keyattr_dynamic=True)

        logger.debug(f'geting device defaults of {ip}')
        """
        the prefix path is used to get the default values of a device
        The path consists of the individual subpaths eg when the device 
        has the IP address 192.168.0.1 the path could be 
        192.168.0.1 / 192.168.0.0/16 / 0.0.0.0/0
        0.0.0.0 should always exist and set the default values.
        """
        prefix_path = tools.get_prefix_path(all_defaults, ip)
        defaults = benedict(keyattr_dynamic=True)
        for prefix in prefix_path:
            for key, value in all_defaults[prefix].items():
                # logger.debug(f'key: {key} value: {value}')
                defaults[key] = value

        return defaults

    def get_device_defaults(self, host_or_ip, device_dict) -> dict:
        """get defaults from our onboarding config and the inventory

        Parameters
        ----------
        host_or_ip : str
            hostname or ip of device
        device_dict : dict
            default values from inventory

        Returns
        -------
        dict
            The merged device defaults of the device
        """
        if not self._all_defaults:
            self._all_defaults = self.get_default_values_from_repo()

        # get default values from SOT / the lowest priority is the prefix default
        logger.debug('getting get_device_defaults_from_prefix')
        device_defaults = self.get_device_defaults_from_prefix(self._all_defaults, host_or_ip)
        for key, value in device_defaults.items():
            logger.bind(extra='dfl').trace(f'key={key} value={value}')

        saved_tags = device_defaults.get('tags')

        # the second priority is the inventory
        for key, value in dict(device_dict).items():
            # do not overwrite values with None
            if value is not None:
                if key in device_defaults:
                    logger.bind(extra='inv (=)').trace(f'key={key} value={value}')
                else:
                    logger.bind(extra='inv (+)').trace(f'key={key} value={value}')
            else:
                del device_dict[key]

        # we have to do a deep merge. We do not want to overwrite values
        # always_merger: always try to merge. in the case of mismatches, the value 
        # from the second object overrides the first one.
        # this merge is descructive!!!
        result = always_merger.merge(device_defaults, device_dict)

        # tags is a list. We have to merge these two lists
        if saved_tags and 'tags' in device_dict:
            if isinstance (saved_tags, str):
                saved_tags = [ saved_tags ]
            if isinstance (device_dict['tags'], str):
                device_dict['tags'] = [ device_dict['tags'] ]
            result['tags'] = saved_tags + device_dict['tags']

        # save default; we need the default values later again
        self._device_defaults = result
        return self._device_defaults

    def read_config_and_facts_from_file(self, hostname):
        device_config = ""
        device_facts = {}

        directory = self._onboarding_config.get('directories', {}).get('export','export')

        config_filename = "./%s/%s.conf" % (directory, hostname.lower())
        facts_filename = "./%s/%s.facts" % (directory, hostname.lower())
        logger.debug(f'reading config from {config_filename} and facts from {facts_filename}')

        try:
            with open(config_filename, 'r') as f:
                device_config = f.read()
            with open(facts_filename, 'r') as f:
                device_facts = json.load(f)
        except Exception as exc:
            logger.error(f'failed to import config or facts {exc}', exc_info=True)
            return None, None

        return device_config, device_facts

    def get_device_config_and_facts(self, 
                                    device_ip, 
                                    device_defaults, 
                                    import_config=False,
                                    import_filename=None,
                                    ssh_port=22):
        """get config and facts from the device or import it from disk"""

        device_facts = {}
        conn = dm.Devicemanagement(ip=device_ip,
                                   platform=device_defaults.get('platform','ios'),
                                   manufacturer=device_defaults.get('manufacturer','cisco'),
                                   username=self._username,
                                   password=self._password,
                                   port=ssh_port,
                                   scrapli_loglevel='none')

        if import_config:
            return self.read_config_and_facts_from_file(import_filename)

        # retrieve facts like fqdn, model and serialnumber
        logger.debug('now gathering facts')
        device_facts = conn.get_facts()

        if device_facts is None:
            logger.error('got no facts; skipping device')
            if conn:
                conn.close()
            return None, None
        device_facts['args.device'] = device_ip

        # retrieve device config
        logger.debug("getting running-config")
        try:
            device_config = conn.get_config("running-config")
        except Exception as exc:
            logger.error(f'failed to receive device config from {device_ip}; got exception {exc}', exc_info=True)
            return None, None
        if device_config is None:
            logger.error(f'failed to retrieve device config from {device_ip}')
            conn.close()
            return None, None
        conn.close()

        return device_config, device_facts

    def get_default_values_from_repo(self):
        """get default values of prefixes"""
        name_of_repo = self._onboarding_config['git']['defaults']['repo']
        path_to_repo = self._onboarding_config['git']['defaults']['path']
        filename = self._onboarding_config['git']['defaults']['filename']
        logger.debug(f'reading {filename} from {name_of_repo}')
        default_repo = veritas.repo.Repository(repo=name_of_repo, path=path_to_repo)
        if default_repo.has_changes():
            logger.warning(f'repo {name_of_repo} has changes')
        defaults_str = default_repo.get(filename)
        if defaults_str is None:
            logger.error("could not load defaults")
            raise Exception('could not load defaults')

        # read the default values from our YAML file
        # the default values are wvery important. Using this values you
        # can easily import dozens of devices. To achieve this use default
        # values like 'unknown' or 'default-location'. After adding the devices
        # use the kobold script to modify tags, custom fields or mandatory
        # properties. 
        try:
            defaults_yaml = yaml.safe_load(defaults_str)
            if defaults_yaml is not None and 'defaults' in defaults_yaml:
                return defaults_yaml['defaults']
        except Exception as exc:
            logger.critical(f'failed to read default values; got exception: {exc}', exc_info=True)
            raise Exception("failed to read default values")

    def device_in_sot(self, ip, hostname):
        """check if device is already in sot"""
        # we have two cases; we have the name of the device (simple)
        # or just the IP address (use graphql to get device)
        logger.debug(f'ip: {ip} hostname: {hostname}')
        if ip == hostname:
            # we have an IP; get device object
            device_in_nb = self._sot.get.device_by_ip(ip=ip)
        else:
            device_in_nb = self._sot.get.device(name=hostname)

        logger.debug(f'address {ip} belongs to {device_in_nb}')
        return device_in_nb

    def extend_device_properties(self, properties):
        """ we have to modify some attributes like device_type and role
           but only if the value is not a dict"""

        for item in ['role', 'manufacturer', 'platform', 'status']:
            if item in properties and not isinstance(properties[item], dict):
                properties[item] = {'name': properties[item]}

        if 'device_type' in properties and not isinstance(properties['device_type'], dict):
            properties['device_type'] = {'model': properties['device_type']}

    def get_primary_address(self):
        """return primary address of device depending on the configured 
           list of interfaces in our onboardign config"""

        # get list of interfaces from config (the order is important; it is first match)
        interfaces = self._onboarding_config.get('onboarding', {}) \
                                            .get('defaults', {}) \
                                            .get('interface', [])

        # loop through device config and check if we find the interface
        for iface in interfaces:
            logger.debug(f'looking if {iface} is primary interface')
            if self._configparser.get_ipaddress(iface) is not None:
                return self._configparser.get_ipaddress(iface)
            else:
                logger.debug(f'no ip address on {iface} found')

        return None

    def get_primary_interface(self, primary_address, device_properties=None):

        """return primary interface of device
        
        there are two cases:

        - the user has defined the primary interface in the inventory or 
        - we have to check the device config to get the orimary interface
        
        If we find the primary interface in the device properties we have to 
        check if it is only the name or if it is a dict containing most of the 
        config we need
        """

        if not device_properties and self._device_properties:
            device_properties = self._device_properties

        if 'primary_interface' in device_properties:
            if isinstance(device_properties['primary_interface'], dict):
                # it is a dict but let's see if the user has specified an IP address
                if 'address' not in device_properties['primary_interface']:
                    device_properties['primary_interface']['address'] = primary_address
                return device_properties['primary_interface']
            else:
                # in this case the user wants to overwrite the primary interface but we have no
                # IP address yet. We use the primary IP we got so far.
                primary_interface = {'name': device_properties['primary_interface'],
                                     'address': primary_address
                                    }
        else:
            # in this case we have to get the primary interface from the device config
            primary_interface = _get_primary_interface_by_address(primary_address, self._configparser)

        return primary_interface

    def get_device_properties(self):
        """get device properties"""

        device_properties = dict(self._device_defaults)
        _get_device_properties(self._sot,
                               device_properties,
                               self._device_facts, 
                               self._configparser, 
                               self._onboarding_config)
    
        if not device_properties:
            return None

        # we have to "adjust" the device properties
        # this methods transforms some values to a dict 
        # eg. role = myrole to {'role': {'name': 'myrole'}}
        self.extend_device_properties(device_properties)

        # The user can configure tags through the "inventory". 
        # In this case, we need to convert tags into a list.
        tags = self._device_defaults.get('tags')
        if isinstance(tags, str):
            logger.debug('adding tag to device_properties')
            device_properties['tags'] = tags.split(',')
            logger.bind(extra='onb (=)').trace(f'key=tags value={tags}')

        # save properties for later use
        self._device_properties = device_properties

        return device_properties

    def get_vlan_properties(self, device_properties=None):
        """get VLAN properties of device"""

        if not device_properties:
            device_properties = self._device_properties

        return _get_vlan_properties(self._configparser, device_properties)

    def get_interface_properties(self):
        """get interface properties of the device"""

        return _get_interface_properties(self._device_defaults, 
                                         self._configparser)

    def add_device_to_sot(self, 
                          device_properties,
                          primary_interface, 
                          interfaces, 
                          vlan_properties,
                          add_prefix=False):

        return self._sot.onboarding \
                .interfaces(interfaces) \
                .vlans(vlan_properties) \
                .primary_interface(primary_interface) \
                .add_prefix(add_prefix) \
                .add_device(device_properties)

    def update_device_in_sot(self, device, primary_address, interfaces, update_interfaces, primary_only=True):
        """update device in sot"""

        if update_interfaces or primary_only:
            all_interfaces = self._sot.get.interfaces(device_id=device.id)

        if update_interfaces:
            # if args.interfaces is set we add unknown interfaces to SOT
            # and update ALL known interfaces as well
            new_interfaces = []
            for interface in interfaces:
                interface_name = interface.get('name','')
                found = False
                for nb_interface in all_interfaces:
                    if interface_name == nb_interface.display:
                        found = True
                        nb_interface.update(interface)
                        logger.debug(f'updated interface {interface_name}')
                if not found:
                    logger.debug(f'interface {interface_name} not found in SOT')
                    new_interfaces.append(interface)
            if len(new_interfaces) > 0:
                self._sot.onboarding \
                     .add_prefix(False) \
                     .assign_ip(True) \
                     .add_interfaces(device=device, interfaces=new_interfaces)
                logger.debug(f'added {len(new_interfaces)} interface(s)')
        elif primary_only:
            # update primary interface
            for interface in interfaces:
                interface_name = interface.get('name','')
                primary_interface_found = False
                for nb_interface in all_interfaces:
                    if interface_name == nb_interface.display:
                        primary_interface_found = True
                        self._sot.onboarding \
                                 .add_prefix(False) \
                                 .assign_ip(True) \
                                .update_interfaces(device=device, interfaces=interfaces)
                        logger.debug(f'updated primary interface {interface_name}')
                if not primary_interface_found:
                    logger.debug('no primary inteface found; seems to be a new one; adding it')
                    self._sot.onboarding \
                             .add_prefix(False) \
                             .assign_ip(True) \
                             .add_interfaces(device=device, interfaces=interfaces)

        # maybe the primary IP has changed. Check it and update if necessary
        if device.primary_ip4:
            current_primary_ip = device.primary_ip4.display.split('/')[0]
        else:
            # there is no primary IP
            current_primary_ip = "unknown or none"
            logger.debug(f'the device {device.display} has no primary IP configured; setting it now')
        if current_primary_ip != primary_address:
            logger.debug(f'updating primary IP of device {device.display} {current_primary_ip} vs. {primary_address}')
            self._sot.onboarding.set_primary_address(primary_address, device)

    def get_tag_properties(self, device_fqdn, device_properties, device_facts):
        """get tag properties"""
        return _get_tag_properties(device_fqdn, 
                                   device_properties, 
                                   device_facts, 
                                   self._configparser, 
                                   self._onboarding_config)

    def add_tags(self, hostname, tag_properties, device=None):
        """add device and interface tags to device"""

        device_tags = []
        interface_tags = {}

        if not device:
            device = sot.get.device(name=hostname)

        for tag in tag_properties:
            if tag.get('scope') == 'dcim.device':
                device_tags.append({'name': tag.get('name')})
            if tag.get('scope') == 'dcim.interface':
                interface_name = tag.get('interface')
                if interface_name not in interface_tags:
                    interface_tags[interface_name] = []
                interface_tags[interface_name].append({'name': tag.get('name')})

        # add device scope tags
        logger.debug(f'device_tags: {device_tags}')
        if len(device_tags) > 0:
            try:
                logger.info(f'adding tags {device_tags} to device')
                device.update({'tags': device_tags})
            except Exception as exc:
                logger.error(f'failed to add device tags {exc}')

        # add interface scope tags
        logger.debug(f'interface_tags: {interface_tags}')
        if len(interface_tags) > 0:
            for interface_name in interface_tags:
                iface = self._sot.get.interface(device_id=device.id, 
                                                name=interface_name)
                try:
                    logger.info(f'adding tags {interface_tags[interface_name]} to {iface}')
                    iface.update({'tags': interface_tags[interface_name]})
                    return True
                except Exception as exc:
                    logger.error(f'failed to add interface tags {exc}')

        return False

