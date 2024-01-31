from __future__ import annotations
from loguru import logger
from pynautobot.models.ipam import IpAddresses

# veritas
from veritas.tools import tools
from veritas.sot import sot

class Onboarding:
    """Class to onboard devices including interfaces, vlans, tags an d further more

    onboarding is used to add devices to nautobot. All necessary properties including
    interfaces, vlans, primary interfaces or IP addresses can be added in one single 
    call to onboarding.

    Parameter
    ----------
    sot : sot
        sot object

    Examples
    --------
    >>> sot.onboarding.interfaces(list_of_interfaces_properties)
    ...               .vlans(list_of_vlans_properties)
    ...               .primary_interface(name_of_primary_interface)
    ...               .add_prefix(False)
    ...               .add_device(device_properties)


    """    

    def __init__(self, sot: sot) -> None:
        self._sot = sot
        self._make_interface_primary = False
        self._primary_interface = ""
        self._is_primary = False
        self._interfaces = []
        self._vlans = []
        self._add_prefix = True
        self._assign_ip = True
        self._bulk = True
        self._use_device_if_already_exists = True
        self._use_interface_if_already_exists = True
        self._use_ip_if_already_exists = True

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    # ---------- fluent attributes ----------

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

    # ---------- user commands ----------

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
        >>> sot.onboarding.interfaces(list_of_interfaces_properties)
        ...               .vlans(list_of_vlans_properties)
        ...               .primary_interface(name_of_primary_interface)
        ...               .add_prefix(False)
        ...               .add_device(device_properties)

        """
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        logger.debug(f'properties: {properties}')

        # add device to nautobot
        device = self._add_device_to_nautobot(properties)

        # first of all VLANs are added to the SOT
        if device and len(self._vlans) > 0:
            self._add_vlans_to_nautobot()

        # now add the interfaces of this device
        # either the interfaces are part of our properties or were
        # configured using .interface(list_of_ifaces)
        interfaces = properties.get('interfaces', self._interfaces)
        self.add_interfaces(device=device, interfaces=interfaces)

        return device

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
            interface_name = interface['name']
            if interface and 'port-channel' in interface_name.lower():
                virtual_interfaces.append(interface)
            else:
                physical_interfaces.append(interface)
        logger.debug(f'summary: adding {len(virtual_interfaces)} virtual '
                     f'and {len(physical_interfaces)} physical interfaces')

        if device and len(interfaces) > 0:
            # add interfces to nautobot
            v_response = self._add_interfaces_to_nautobot(device, virtual_interfaces)
            p_response = self._add_interfaces_to_nautobot(device, physical_interfaces)
            # the interfaces were added; now add the IP addresses of ALL interfaces
            for interface in interfaces:
                ip_addresses = interface.get('ip_addresses',[])
                # an interface can have more than one IP, so it is a list of IPs!!!
                if len(ip_addresses) > 0:
                    logger.debug(f'found {len(ip_addresses)} IP(s) on device {device} '
                                 f'{interface.get("name")}')
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
                                    assign = self._assign_ipaddress_to_interface(device, nb_interface, ip_address)
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
                                self._assign_ipaddress_to_interface(device, nb_interface, ip_address)
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
            return device.update({'primary_ip4': ip_address.id})
        except Exception as exc:
            if 'is not assigned to this device' in str(exc):
                logger.error(f'the address {ip_address.display} is not assigned to {device.name}')
                return False

    # ---------- private methods ----------

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

        """
        try:
            device_name = device_properties.get('name')
            logger.info(f'adding device {device_name} to SOT')
            device = self._nautobot.dcim.devices.create(device_properties)
            if device is None:
                logger.error(f'could not add device {device_name} to SOT')
                return None
            return device
        except Exception as exc:
            if 'A device with this name already exists' in str(exc):
                logger.debug('a device with this name already exists')
                if self._use_device_if_already_exists:
                    return self._nautobot.dcim.devices.get(name=device_name)
            else:
                logger.error(exc)
        return None 

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
        try:
            return self._nautobot.ipam.vlans.create(new_vlans)
        except Exception as exc:
            logger.error(exc)
        return False

    def _add_interfaces_to_nautobot(self, device, interfaces:list):
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
        logger.debug(f'adding {len(interfaces)} interfaces to device {device}')
        for interface in interfaces:
            if 'device' not in interface:
                interface['device'] = {'id': device.id}
            if 'lag' in interface:
                interface['lag']['device'] = device.id
        if self._bulk:
            try:
                return self._nautobot.dcim.interfaces.create(interfaces)
            except Exception as exc:
                if 'The fields device, name must make a unique set' in str(exc):
                    logger.error('one or more interfaces were already in nautobot')
                else:
                    logger.error('got exception: {exc}')
                    logger.debug('failed interfaces: {interfaces}')
                return False
        else:
            for interface in interfaces:
                success = True
                try:
                    # if one request failes we return False
                    success = success and self._nautobot.dcim.interfaces.create(interface)
                except Exception as exc:
                    if 'The fields device, name must make a unique set' in str(exc):
                        logger.error('this interfaces is already in nautobot')
                    success = False
            return success

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
            try:
                added_prefixe.append(self._nautobot.ipam.prefixes.create(properties))
            except Exception as exc:
                logger.error(f'could not add prefix to nautobot; got {exc}')

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
            try:
                added_addresses.append(self._nautobot.ipam.ip_addresses.create(properties))
                logger.debug(f'added IP {ip_address} to nautobot')
            except Exception as exc:
                if 'duplicate key value violates unique constraint' in str(exc):
                    logger.debug(f'IP {ip_address} namespace: {namespace} address already exists; '\
                        f'return_ip={self._use_ip_if_already_exists}')
                    if self._use_ip_if_already_exists:
                        addr = self._nautobot.ipam.ip_addresses.get(
                            address=ip_address.split('/')[0], 
                            namespace=namespace)
                        logger.debug(f'got IP {addr}')
                        added_addresses.append(addr)
                else:
                    logger.error(exc)
        return added_addresses 

    def _assign_ipaddress_to_interface(self, device, interface, ip_address) -> bool:
        """private method to assign IPv4 address to interface set primary IPv4

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
            properties = {'interface': interface.id,
                          'ip_address': ip_address.id} 
            assigned = self._nautobot.ipam.ip_address_to_interface.create(properties)
        except Exception as exc:
            if 'The fields interface, ip_address must make a unique set.' in str(exc):
                logger.debug('this IP address is already assigned')
                assigned = True
            else:
                assigned = False
                logger.error(exc)
        
        if assigned and str(interface.display).lower() == self._primary_interface.lower():
            logger.debug('found primary IP; update device and set primary IPv4')
            try:
                device.update({'primary_ip4': ip_address.id})
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
        ip_addresses = self._nautobot.ipam.ip_addresses.filter(device_id=[device.id], interfaces=interface.display)
        for ip in ip_addresses:
            id_list = self._nautobot.ipam.ip_address_to_interface.filter(
                interface=interface.display, 
                ip_address=ip.id)
            response = True
            for assignment in id_list:
                try:
                    assignment.delete()
                except Exception as exc:
                    logger.error(exc)
                    response = False
        return response
