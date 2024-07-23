from __future__ import annotations
import os
import yaml
import json
import socket
import csv
import importlib
import sys
import pathlib
from ipaddress import IPv4Network
from loguru import logger
from benedict import benedict
from deepmerge import always_merger
from pynautobot.models.ipam import IpAddresses

# veritas
import veritas.repo
from veritas.sot import sot
from veritas.tools import tools
from veritas.onboarding.tags import get_tag_properties as _get_tag_properties
from veritas.onboarding import plugins
from veritas.tools import exceptions as veritas_exceptions


class Onboarding():

    def __init__(self, sot=None, onboarding_config=None, 
                 profile=None, tcp_port=22):

        self._sot = sot
        self._onboarding_config = onboarding_config
        self._profile = profile
        self._tcp_port = tcp_port

        self._all_defaults = None
        self._configparser = None
        self._device_config = None
        self._device_facts = None
        self._device_defaults = None
        self._device_properties = None

        # load plugins
        logger.debug('importing standard onboarding_plugins')
        importlib.import_module('veritas.configparser.cisco_configparser')
        self._load_module('config_and_facts', 'onboarding_plugins', 'ios_config_and_facts')
        self._load_module('device_properties', 'onboarding_plugins', 'ios_device_properties')
        self._load_module('interface_properties', 'onboarding_plugins', 'ios_interface_properties')
        self._load_module('vlan_properties', 'onboarding_plugins', 'ios_vlan_properties')

        # fluent interface
        self._interfaces = []
        self._vlans = []
        self._primary_interface = ""
        self._use_device_if_already_exists = True
        self._use_interface_if_already_exists = True
        self._use_ip_if_already_exists = True
        self._add_prefix = True
        self._assign_ip = True
        self._bulk = True
        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    # fluent interface

    def interfaces(self, *unnamed, **named) -> Onboarding:
        """add interface to nautobot

        Parameters
        ----------
        *unnamed
            unnamed arguments that are passed to create interfaces
        **named
            named arguments that are passed to create interfaces

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax
        - The arguments are saved as list for later use.

        interfaces look like::

            interfaces = [{'name': 'GigabitEthernet 0/0',
                                   'ip_addresses': [{'address': '192.168.0.1/24',
                                                     'status': {'name': 'Active'}
                                                    }],
                                   'description': 'Primary Interface',
                                   'type': '1000base-t',
                                   'status': {'name': 'Active'}
                         }]


        """
        logger.debug('adding interface to list of interfaces')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        # we start with an empty list!
        self._interfaces = []

        if isinstance (properties, list):
            for property in properties:
                self._interfaces.append(property)
        else:
            self._interfaces.append(properties)

        return self

    def vlans(self, *unnamed, **named) -> Onboarding:
        """add vlans to nautobot

        Parameters
        ----------
        *unnamed
            unnamed arguments that are passed to create vlans
        **named
            named arguments that are passed to create vlans

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax
        - The arguments are saved as list for later use.

        vlans look like::

            vlans = [{'name': 'my_vlan',
                      'vid': 100,
                      'status': {'name': 'Active'},
                      'location': 'location_name
                    }]

        """
        logger.debug('adding vlan to list of VLANS')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        # we start with an empty list
        self._vlans = []
        if isinstance (properties, list):
            for property in properties:
                self._vlans.append(property)
        else:
            self._vlans.append(properties)

        return self

    def primary_interface(self, primary_interface:str) -> Onboarding:
        """segt primary interface

        Parameters
        ----------
        primary_interface
            name of the primary interface

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax
        - The argument is saved as str for later use.

        """
        logger.debug(f'setting primary interface to {primary_interface}')
        self._primary_interface = primary_interface
        return self

    def use_device_if_exists(self, use_device: bool) -> Onboarding:
        """if device already exist return device instead of error

        Parameters
        ----------
        use_device : bool
            True if device should be returned otherwise False

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax

        """
        logger.debug(f'setting _use_device_if_already_exists to {use_device}')
        self._use_device_if_already_exists = use_device

        return self

    def use_interface_if_exists(self, use_interface: bool) -> Onboarding:
        """return interface if interface exists instead of error

        Parameters
        ----------
        use_interface : bool
            True if interface should be returned otherwise False

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax

        """
        logger.debug(f'setting _use_interface_if_already_exists to {use_interface}')
        self._use_interface_if_already_exists = use_interface
        return self

    def use_ip_if_exists(self, use_ip:bool) -> Onboarding:
        """return IP if IP exists instead of error

        Parameters
        ----------
        use_ip : bool
            True if IP should be returned otherwise False

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax

        """
        logger.debug(f'setting _use_ip_if_already_exists to {use_ip}')
        self._use_ip_if_already_exists = use_ip
        return self

    def add_prefix(self, add_prefix:bool) -> Onboarding:
        """add prefix to nautobot

        Parameters
        ----------
        add_prefix : bool
            if True add prefix to nautobot

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax

        Examples
        --------

        """
        logger.debug(f'setting _add_prefix to {add_prefix}')
        self._add_prefix = add_prefix
        return self

    def assign_ip(self, assign_ip:bool) -> Onboarding:
        """assign IP to device

        Parameters
        ----------
        assign_ip : bool
            if True assign IP to device

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax
        """
        logger.debug(f'setting _assign_ip to {assign_ip}')
        self._assign_ip = assign_ip
        return self

    def bulk(self, bulk:bool) -> Onboarding:
        """use bulk to add data to nautobot

        Parameters
        ----------
        bulk : bool
            if True use bulk method to insert data

        Returns
        -------
        Onboarding
            the onboarding object
        
        Notes
        -----
        - we use this method to implement the fluent syntax
        """
        logger.debug(f'setting _bulk to {bulk}')
        self._bulk = bulk
        return self

    # fluent and non fluent commands

    def add_device(self, *unnamed, **named):
        """add device to nautobot

        The device including vlans and interfaces are added to nautobot.
        The IP assignment as well as adding the prefixes to nautobot and setting the pimary
        IP is done as well.

        Parameters
        ----------
        *unnamed
            unnamed arguments that are passed to add device
        **named
            named arguments that are passed to add device

        Returns
        -------
        device : `nautobot.dcim.devices`
            the device added to nautobot
        
        See Also
        --------
        interfaces
        vlans
        primary_interface
        assign_ip
        add_prefix

        Notes
        -----
        You an use named AND unnamed parameter. This functions converts ALL parameter to
        one property and passes it to the underlaying methods.

        Examples
        --------
        >>> onboarding.interfaces(list_of_interfaces_properties)
        ...           .vlans(list_of_vlans_properties)
        ...           .primary_interface(name_of_primary_interface)
        ...           .add_prefix(False)
        ...           .add_device(device_properties)

        """
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        # if this method is called without the fluent
        # interface you can set the properties as well
        if 'interfaces' in properties:
            self._interfaces = properties['interfaces']
            del properties['interfaces'] 
        if 'vlans' in properties:
            self._vlans = properties['vlans']
            del properties['vlans']
        if 'primary_interface' in properties:
            self._primary_interface = properties['primary_interface']
            del properties['primary_interface']
        if 'add_prefix' in properties:
            self._add_prefix = properties['add_prefix']
            del properties['add_prefix']

        # add device to nautobot
        device = self._add_device_to_nautobot(properties)

        if not device:
            logger.error('failed to add device to nautbot')
            return False

        # first of all VLANs are added to the SOT
        if device and len(self._vlans) > 0:
            self._add_vlans_to_nautobot()

        # now add the interfaces of this device
        # either the interfaces are part of our properties or were
        # configured using .interface(list_of_ifaces)
        interfaces = properties.get('interfaces', self._interfaces)
        self.add_interfaces(device=device, interfaces=interfaces)

        return device

    # private fluent commands

    def add_interfaces(self, device, interfaces:list) -> bool:
        """add interfaces to nautobot

        Add interfaces to nautobot. This method is normally called by add_device.
        Physical interfaces like GigabitEthernetx/y and logical interfaces like port-channels
        are added to nautobot. 
        The IP address(es) of the interfaces are also added to nautobot when calling this method.

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        interfaces : list
            list of interfaces to add

        Returns
        -------
        success : bool
            True if interfaces were added

        See Also
        --------
        add_device

        Examples
        --------
        >>> sot.onboarding.add_prefix(False)
        ...               .assign_ip(True)
        ...               .add_interfaces(device=device_obj, interfaces=list_of_interfaces)
        """
        logger.debug(f'adding interfaces to {device}')

        v_response = p_response = prefix = assign = True
        # now add the virtual and physical interfaces
        virtual_interfaces = []
        physical_interfaces = []
        for interface in interfaces:
            interface_type = interface.get('type')
            #if interface and 'port-channel' in interface_name.lower():
            if interface and interface_type.lower() == 'lag':
                virtual_interfaces.append(interface)
            else:
                physical_interfaces.append(interface)
        logger.debug(f'summary: adding {len(virtual_interfaces)} virtual '
                     f'and {len(physical_interfaces)} physical interfaces')

        if device and len(interfaces) > 0:
            # add interfces to nautobot
            v_response = self._add_interfaces_to_nautobot(device, virtual_interfaces, 'virtual')
            p_response = self._add_interfaces_to_nautobot(device, physical_interfaces, 'physical')
            # the interfaces were added; now add the IP addresses of ALL interfaces
            for interface in interfaces:
                ip_addresses = interface.get('ip_addresses',[])
                logger.debug(f'found {len(ip_addresses)} IP(s) on device {device}/'
                             f'{interface.get("name")}')
                # an interface can have more than one IP, so it is a list of IPs!!!
                if len(ip_addresses) > 0:
                    # add description to each IP address
                    for addr in ip_addresses:
                        addr['description'] = f'{device} {interface.get("name")}'
                    if self._add_prefix:
                        prefix = self._add_prefix_to_nautobot(ip_addresses)

                    added_addresses = self._add_ipaddress_to_nautbot(device, ip_addresses)
                    if len(added_addresses) > 0:
                        # get interface object from nautobot
                        nb_interface = self._nautobot.dcim.interfaces.get(
                                    device_id=device.id,
                                    name=interface.get('name'))
                        for ip_address in added_addresses:
                            if self._assign_ip:
                                if nb_interface:
                                    assign = self._assign_ip_and_set_primary(device, nb_interface, ip_address)
                                    logger.debug(f'assigned IPv4 {ip_address} on device {device} / nb_interface')
                                else:
                                    logger.error(f'could not get interface {device.name}/{interface.get("name")}')

        # todo: what value should we return?
        return v_response and p_response and prefix and assign

    def update_interfaces(self, device, interfaces:list) -> bool:
        """update interface of a device

        Update interface of a device.

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        interfaces : list
            list of interfaces to add

        Returns
        -------
        success : bool
            True if successful
        
        See Also
        --------
        add_device
        add_interfaces

        Examples
        --------
        >>> sot.add_prefix(False)
        ...    .assign_ip(True)
        ...    .update_interfaces(device=device_obj, interfaces=list_of_interfaces)


        """
        logger.debug(f'updating interfaces of {device}')

        if not device or len(interfaces) == 0:
            logger.error('either no device found or len(interfaces) == 0')
            return False

        for interface in interfaces:
            # get interface object from nautobot
            nb_interface = self._nautobot.dcim.interfaces.get(
                            device_id=device.id,
                            name=interface.get('name'))
            nb_interface.update(interface)

            # remove ALL assigments
            self._remove_all_assignments(device, nb_interface)

            ip_addresses = interface.get('ip_addresses',[])
            # an interface can have more than one IP, so it is a list of IPs!!!
            # we are now (re)adding all assigments
            if len(ip_addresses) > 0:
                logger.debug(f'found {len(ip_addresses)} IP(s) on device {device} {interface.get("name")}')
                # add description to each IP address
                for addr in ip_addresses:
                    addr['description'] = f'{device} {interface.get("name")}'
                if self._add_prefix:
                    self._add_prefix_to_nautobot(ip_addresses)
                
                added_addresses = self._add_ipaddress_to_nautbot(device, ip_addresses)
                if len(added_addresses) > 0:
                    for ip_address in added_addresses:
                        if self._assign_ip:
                            if nb_interface:
                                self._assign_ip_and_set_primary(device, nb_interface, ip_address)
                                logger.debug(f'assigned IPv4 {ip_address.display} on device {device} / nb_interface')
                            else:
                                logger.error(f'could not get interface {device.name}/{interface.get("name")}')
        return True

    def set_primary_address(self, address, device) -> bool:
        """set primary interface of a device

        Update interface of a device.

        Parameters
        ----------
        address
            IP address of the device
        device : nautobot.dcim.devices
            the device

        Returns
        -------
        success : bool
            True if successful
        
        Notes
        -----
        address can either be a str or nautobot.ipam.ip_address

        """
        if isinstance(address, str):
            ip_address = self._nautobot.ipam.ip_addresses.get(address=address)
        else:
            ip_address = address
        if not isinstance(ip_address, IpAddresses):
            logger.error('no valid ip address found')
            return False
        
        try:
            logger.debug(f'setting primary ip4 of {device.display} to {ip_address.display} ({ip_address.id})')
            #return device.update({'primary_ipv4': ip_address.id})
            success = device.primary_ip4 = ip_address
            device.save()
            return success
        except Exception as exc:
            if 'is not assigned to this device' in str(exc):
                logger.error(f'the address {ip_address.display} is not assigned to {device.name}')
                return False

    def _add_device_to_nautobot(self, device_properties:dict):
        """private method to add device to nautobot

        Parameters
        ----------
        device_properties : dict
            device_properties

        Returns
        -------
        device : nautobot.dcim.devices
            nautobot.dcim.devices or None if not successfull

        Raises:
            error when adding device to nautobot
            the exception is forwarded from pynautobot to the app

        """
        try:
            device_name = device_properties.get('name')
            logger.info(f'adding device {device_name} to SOT')
            logger.trace(f'device_properties={device_properties}')
            device = self._nautobot.dcim.devices.create(device_properties)
            if device is None:
                logger.error(f'could not add device {device_name} to SOT')
                return None
            return device
        except Exception as exc:
            if 'A device with this name already exists' in str(exc) and self._use_device_if_already_exists:
                logger.debug('a device with this name already exists')
                return self._nautobot.dcim.devices.get(name=device_name)
            else:
                raise exc

    def _add_vlans_to_nautobot(self):
        """private method to add vlans to nautobot

        Returns
        -------
        success
            nautobot.dcim.devices if success otherwise None

        """
        logger.debug('adding VLANs to nautobot')
        # check if vlan exists
        new_vlans = []
        for vlan in self._vlans:
            vid = vlan.get('vid')
            location = vlan.get('location')
            # uuid = self._sot.get.id(item='vlan', vid=vid, location=location)
            uuid = self._sot.get.vlans(vid=vid, location=location, get_single_id=True)
            if uuid:
                logger.debug(f'vlan vid={vid} location={location} found in nautobot')
            else:
                new_vlans.append(vlan)
        return self._nautobot.ipam.vlans.create(new_vlans)

    def _add_interfaces_to_nautobot(self, device, interfaces:list, debug_msg=''):
        """private method to add interfaces to nautobot

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        interfaces : list
            list of interfaces

        Returns
        -------
        success : bool
            True if successful

        """
        logger.debug(f'adding {len(interfaces)} {debug_msg} interfaces to device {device}')
        for interface in interfaces:
            if 'device' not in interface:
                interface['device'] = {'id': device.id}
            if 'lag' in interface:
                interface['lag']['device'] = device.id
        if self._bulk:
            return self._nautobot.dcim.interfaces.create(interfaces)
        else:
            for interface in interfaces:
                self._nautobot.dcim.interfaces.create(interface)

            return True

    def _add_prefix_to_nautobot(self, ip_addresses:list) -> list:
        """private method to add prefixes to nautobot

        Parameters
        ----------
        ip_addresses : list
            list of IP addresses

        Returns
        -------
        added_prefixe : list
            list of prefixes added

        """
        added_prefixe = []
        for ipaddress in ip_addresses:
            parent = ipaddress.get('parent')
            if not parent:
                logger.debug('could not get parent')
                continue
            properties = {
                'prefix': parent.get('prefix'),
                'namespace': parent.get('namespace',{}).get('name'),
                'status': {'name': 'Active'}
            }
            added_prefixe.append(self._nautobot.ipam.prefixes.create(properties))
        return added_prefixe

    def _add_ipaddress_to_nautbot(self, device, addresses:list) -> list:
        """private method to add IP addresses to nautobot

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        addresses : list
            list of IP adresses

        Returns
        -------
        added_addresses : list
            list of IP addresses added

        """
        added_addresses = []

        # mandatory parameters are address, status and namespace
        # we get the hldm (or part of it)
        for address in addresses:
            ip_address = address.get('address')
            status = address.get('status', {'name': 'Active'})
            namespace = address.get('parent',{}).get('namespace',{}).get('name','Global')
            description = address.get('description')

            properties = {'address': ip_address,
                          'status': status,
                          'namespace': namespace}
            if description:
                properties.update({'description': description})
            if 'role' in address and address['role']:
                properties.update({'role': address['role']})
            if 'tags' in address and len(address['tags']) > 0:
                properties.update({'tags': address['tags']})

            # check if ip_address is already in SOT
            addr_in_sot = self._nautobot.ipam.ip_addresses.get(
                            address=ip_address.split('/')[0], 
                            namespace=namespace)
            if addr_in_sot:
                logger.debug(f'IP {ip_address} namespace: {namespace} address already exists; '\
                        f'return_ip={self._use_ip_if_already_exists}')
                if self._use_ip_if_already_exists:
                    added_addresses.append(addr_in_sot)
            else:
                added_addresses.append(self._nautobot.ipam.ip_addresses.create(properties))
                logger.debug(f'added IP {ip_address} to nautobot')

        return added_addresses 

    def _assign_ip_and_set_primary(self, device, interface, ip_address) -> bool:
        """private method to assign IPv4 address to interface and set primary IPv4

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        interface : nautobot.dcim.interfaces
            interface to assign IP to
        ip_address : nautobot.ipam.ip_addresses
            IP address to assign

        Returns
        -------
        assigned : bool
            True if successfull

        """
        logger.debug(f'assigning IP {ip_address} to {device}/{interface.display}')
        try:
            assigned = self._nautobot.ipam.ip_address_to_interface.create(
                {'interface': interface.id,
                 'ip_address': ip_address.id})
        except Exception as exc:
            if 'The fields interface, ip_address must make a unique set.' in str(exc):
                logger.debug('this IP address is already assigned')
                assigned = True
            else:
                assigned = False
                logger.error(exc)
                raise(exc)

        if assigned and str(interface.display).lower() == self._primary_interface.lower():
            logger.debug('found primary IP; update device and set primary IPv4')
            try:
                device.primary_ip4 = ip_address
                device.save()
            except Exception:
                logger.error(f'could not set primary IPv4 on {device}')

        return assigned

    def _remove_all_assignments(self, device, interface):
        """remove all assigments

        Parameters
        ----------
        device : nautobot.dcim.devices
            the device of the interfaces
        interface : nautobot.dcim.interfaces
            interface to assign IP to

        Returns
        -------
        response : bool
            True if successfull

        """
        logger.debug(f'removing ALL assigments on {device.display}/{interface.display}')
        ip_addresses = self._nautobot.ipam.ip_addresses.filter(device=[device], interfaces=interface.id)
        debug_list_of_ip = [ip.display for ip in ip_addresses]
        logger.debug(f'got this list of IP addresses {debug_list_of_ip}')
        response = False
        for ip in ip_addresses:
            id_list = self._nautobot.ipam.ip_address_to_interface.filter(
                interface=interface.id, 
                ip_address=ip.id)
            for assignment in id_list:
                logger.debug(f'delete assignment {device}/{interface.display} {ip}')
                assignment.delete()
            response = True

        return response

    # non fluent commands (class)

    def _load_module(self, name, package, subpackage):
        current_dir = pathlib.Path(__file__).parent.resolve()

        spec = importlib.util.spec_from_file_location(name, f'{current_dir}/{package}/{subpackage}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[subpackage] = module
        spec.loader.exec_module(module)
        return True

    def parse_config(self, device_config, device_facts, device_defaults):
        """parse config and save device_config, device_facst and device_defaults for later use"""
        self._device_config = device_config
        self._device_facts = device_facts
        self._device_defaults = device_defaults

        platform = device_defaults.get('platform','ios')
        
        # we use a plugin to parse the config
        plugin = plugins.Plugin()
        configparser = plugin.get_configparser(platform)
        if not configparser:
            logger.critical(f'failed to load configparser for platform {platform}')
            raise veritas_exceptions.ConfigParserLoadError(
                    f'failed to load configparser for platform {platform}',
                    additional_info=f'platform {platform}') 
        else:
            logger.debug(f'using plugin configparser for platform {platform}')
        self._configparser = configparser(config=device_config, platform=platform)

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
            table = yaml.safe_load(f.read())

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

        logger.debug(f'geting (prefix based) device defaults of {ip}')
        """
        the prefix path is used to get the default values of a device
        The path consists of the individual subpaths eg when the device 
        has the IP address 192.168.0.1 the path could be 
        192.168.0.1 / 192.168.0.0/16 / 0.0.0.0/0
        0.0.0.0 should always exist and set the default values.
        """
        prefix_path = tools.get_prefix_path(all_defaults, ip)
        logger.debug(f'the prefix path is {prefix_path}')
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

        with open(config_filename, 'r') as f:
            device_config = f.read()
        with open(facts_filename, 'r') as f:
            device_facts = json.load(f)

        return device_config, device_facts

    def get_device_config_and_facts(
            self, 
            device_ip, 
            device_defaults, 
            import_config=False,
            import_filename=None):
        """get config and facts from the device or import it from disk"""

        if import_config:
            return self.read_config_and_facts_from_file(import_filename)

        #
        # we use the plugin mechanism to get config and facts
        # part of the default onboarding is cisco ios
        # but the user can register its own plugin to get the config
        #
        platform = device_defaults.get('platform')
        plugin = plugins.Plugin()
        get_caf = plugin.get_config_and_facts(platform)
        if not platform or not get_caf:
            logger.critical(f'failed to get config and facts for platform {platform}')
            raise Exception ('unknown platform')
        return get_caf(
            device_ip, 
            device_defaults, 
            self._profile, 
            self._tcp_port, 
            scrapli_loglevel='none')

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
        # the default values are very important. Using this values you
        # can easily import dozens of devices. To achieve this use default
        # values like 'unknown' or 'default-location'. After adding the devices
        # use the kobold script to modify tags, custom fields or mandatory
        # properties. 
        try:
            defaults_yaml = yaml.safe_load(defaults_str)
            if defaults_yaml is not None and 'defaults' in defaults_yaml:
                # save defaults as all_defaults. We need it to get the default value for
                # each device
                self._all_defaults = defaults_yaml['defaults']
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

    def check_serial(self, serial):
        """check if seerial number is already in sot"""

        return self._sot.get.device_by_serial(serial=serial)

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
            if self._configparser.get_interface_ipaddress(iface) is not None:
                return self._configparser.get_interface_ipaddress(iface)
            else:
                logger.debug(f'no ip address on {iface} found')

        return None

    def get_primary_interface(self, primary_address, device_properties=None):
        """return primary interface of device
        
        there are two cases:

        - the user has defined the primary interface in the inventory or 
        - we have to check the device config to get the primary interface
        
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
            primary_interface = self.get_primary_interface_by_address(primary_address)

        return primary_interface

    def get_primary_interface_by_address(self, primary_address):
        primary_interface = {}
        interface_name = self._configparser.get_interface_name_by_address(primary_address)
        interface = self._configparser.get_interface(interface_name)

        # if we have the correct mask of the interface/ip we use this instead of a /32
        if interface is not None:
            # we modify the interface so we do have to use a copy!
            primary_interface = interface.copy()
            primary_interface['name'] = interface_name
            # convert IP and MASK to cidr notation
            prefixlen = IPv4Network("0.0.0.0/%s" % interface.get('mask')).prefixlen
            primary_interface['cidr'] = "%s/%s" % (interface.get('ip'), prefixlen)
            primary_interface['address'] = interface.get('ip')
            logger.debug(f'found primary interface; setting primary_address interface to {primary_address}')
            if 'description' not in interface:
                logger.info("primary interface has no description configured; using 'primary interface'")
                primary_interface['description'] = "primary interface"
        else:
            logger.debug('found no interface, setting default values')
            primary_interface['name'] = "primaryInterface"
            primary_interface['description'] = "primary interface"
            primary_interface['cidr'] = f'{primary_address}/32'
            primary_interface['address'] = primary_address

        # we use 'address' instead of 'ip' because nautobot uses this name
        if 'ip' in primary_interface:
            del primary_interface['ip']
        return primary_interface

    def get_device_properties(self, use_default=True):
        """get device properties"""

        # we use our plugin architecture to use the right module
        platform = self._device_defaults.get('platform')
        plugin = plugins.Plugin()
        get_dp = plugin.get_device_properties(platform)

        if not get_dp:
            logger.critical(f'failed to get device properties for platform {platform}')
            raise Exception ('unknown platform')

        device_properties = dict(self._device_defaults) if use_default else {}
        obj = get_dp(self._sot, self._device_facts, self._configparser, self._onboarding_config)
        obj.get_device_properties(device_properties)
        if not device_properties:
            return None

        # we have to "adjust" the device properties
        # this methods transforms some values to a dict 
        # eg. role = myrole to {'role': {'name': 'myrole'}}
        self._extend_device_properties(device_properties)

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

        # we use our plugin architecture to use the right module
        platform = self._device_defaults.get('platform')
        plugin = plugins.Plugin()
        get_vp = plugin.get_vlan_properties(platform)

        if not get_vp:
            logger.critical(f'failed to get vlan properties for platform {platform}')
            raise Exception ('unknown platform')

        return get_vp(self._configparser, device_properties)

    def get_interface_properties(self):
        """get interface properties of the device"""

        # we use our plugin architecture to use the right module
        platform = self._device_defaults.get('platform')
        plugin = plugins.Plugin()
        get_ip = plugin.get_interface_properties(platform)

        if not get_ip:
            logger.critical(f'failed to get interface properties for platform {platform}')
            raise Exception ('unknown platform')

        obj = get_ip(self._configparser)
        return obj.get_interface_properties(self._device_defaults)

    def get_tag_properties(self, device_fqdn, device_properties, device_facts):
        """get tag properties"""
        return _get_tag_properties(device_fqdn, 
                                   device_properties, 
                                   device_facts, 
                                   self._configparser, 
                                   self._onboarding_config)

    def set_device_properties(self, device_properties):
        """set device properties"""
        self._device_properties = device_properties

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

    def _extend_device_properties(self, properties):
        """ we have to modify some attributes like device_type and role
           but only if the value is not a dict"""

        for item in ['role', 'manufacturer', 'platform', 'status']:
            if item in properties and not isinstance(properties[item], dict):
                properties[item] = {'name': properties[item]}

        if 'device_type' in properties and not isinstance(properties['device_type'], dict):
            properties['device_type'] = {'model': properties['device_type']}
