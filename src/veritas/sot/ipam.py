from loguru import logger

# veritas
from veritas.tools import exceptions as veritas_exceptions


class Ipam(object):

    def __init__(self, sot):
        # init variables
        self._sot = sot

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def add_ip(self, address):
        """add IP address to ipam"""
        try:
            return self._nautobot.ipam.ip_addresses.create(address)
        except Exception as exc:
            #logger.bind(extra=address.get("address","unset")).error(f'could not add ip address; got exception {exc}')
            logger.error(f'could not add ip address; got exception {exc}')
            return False

    def get_ip(self, address, namespace='Global'):
        """get IP address from ipam"""
        # if there is a / use address only
        address = address.split('/')[0]
        logger.debug(f'getting IP {address} namespace {namespace}')
        return self._nautobot.ipam.ip_addresses.get(address=address,
                                                    namespace=namespace)

    def get_vlans(self, vid=None, name=None, location='', location_type=None,
                  get_single_id=None, get_obj=None, 
                  select=['id', 'vid', 'name', 'location']):
        """return a list of VLANs depending on the arguments"""

        # the list of vlans to return
        response = []

        # set global_vid if user wants to see the global VLANs (without location)
        global_vid = False
        if location == '':
            location = None
        elif not location:
            location = None
            global_vid = True

        using = "nb.vlans"
        where = {'vid': vid, 'name': name}

        vlans = self._sot.get.query(select=select, using=using, where=where, mode='sql')

        # we have all VLANs 
        # unfortunately it is not possible to filter by location or location_type
        # we have to do it manually
        #
        # 1. user has set location and location_type
        # 2. user has set location only
        # 3. user has set location_type and location=None (root/Global)
        #    this case returns an empty set
        # 4. user has set location to None and has not set location_type
        # 5. user has neither set location nor location_type
        logger.debug(f'location: {location} location_type: {location_type} gloval_vid: {global_vid}')
        for vlan in vlans:
            vlan_location = vlan['location']
            if vlan_location:
                vlan_location_type = vlan['location']['location_type']
            else:
                vlan_location_type = None

            if location and location_type:
                if vlan_location and vlan['location'].get('name') == location and \
                   vlan['location']['location_type'].get('name') == location_type:
                   logger.debug('location and location_type match')
                   response.append(vlan)
            elif location:
                if vlan_location and vlan_location.get('name') == location:
                    logger.debug('location matches')
                    response.append(vlan)
            elif location_type and not global_vid:
                # this should aleway be false, or???
                if vlan_location and vlan_location_type.get('name') == location_type:
                    logger.debug('location_type matches')
                    response.append(vlan)
            elif not location_type and global_vid:
                logger.debug('global_vid is set')
                if not vlan_location: 
                    response.append(vlan)
            elif not location and not location_type:
                logger.debug('either location nor location_type set')
                response.append(vlan)

        # if get_single_id is set and we have only one item we only return the id
        if get_single_id and len(response) == 1:
            id = response[0].get('id')
            if get_obj:
                return self._nautobot.ipam.vlans.get(id=id)
            return id
        if get_obj:
            objs = []
            for vlan in response:
                id = vlan.get('id')
                objs.append(self._nautobot.ipam.vlans.get(id=id))
            return objs
        return response

    def get_assignment(self, interface, address, device=None, namespace='Global'):

        if isinstance(interface, str):
            # we need the device to get the interface
            if isinstance(device, str):
                # get nautobot object of device
                nb_device = self._nautobot.dcim.devices.get(name=device)
            else:
                nb_device = device

            if not nb_device:
                logger.error(f'failed to get device {device}')
                return False
            # get nautobot object of interface
            nb_interface = self._nautobot.dcim.interfaces.get(
                device_id=nb_device.id, 
                name=interface)
        else:
            nb_interface = interface

        if isinstance(address, str):
            # get nautobot object of device
            nb_addr = self._nautobot.ipam.ip_addresses.get(
                address=address,
                namespace=namespace)
        else:
            nb_addr = address

        try:
            return self._nautobot.ipam.ip_address_to_interface.get(
                    interface=nb_interface.id, 
                    ip_address=nb_addr.id)
        except Exception as exc:
            logger.error(f'failed to get assignment; got exception {exc}')
            return None

    def get_choices(self):
        return self._nautobot.ipam.ip_addresses.choices()

    def assign_ipaddress_to_interface(self, interface, address, device, namespace='Global') -> bool:
        """private method to assign IPv4 address to an interface

        Parameters
        ----------
        device : str or nautobot.dcim.devices
            the device of the interfaces
        interface : str or nautobot.dcim.interfaces
            interface to assign IP to
        address : str or nautobot.ipam.ip_addresses
            IP address to assign

        Returns
        -------
        assigned : bool
            True if successfull

        """
        nb_interface = self._get_interface_of_device(interface=interface, device=device)

        if isinstance(address, str):
            # get nautobot object of device
            nb_addr = self._nautobot.ipam.ip_addresses.get(
                address=address,
                namespace=namespace)
        else:
            nb_addr = address

        if not nb_addr:
            logger.error(f'failed to get IP address {address}')

        logger.debug(f'assigning IP {address} to {device}/{nb_interface.display}')
        try:
            properties = {'interface': nb_interface.id,
                         'ip_address': nb_addr.id}
            return self._nautobot.ipam.ip_address_to_interface.create(properties)
        except Exception as exc:
            if 'The fields interface, ip_address must make a unique set.' in str(exc):
                logger.debug('this IP address is already assigned')
                return True
            else:
                logger.error(f'failed to assign ip to interface; got exception {exc}')
                return False
        
    def set_primary(self, device, address, namespace='Global'):
        """set primary IP address of device

        Parameters
        ----------
        device : str or nautobot.dcim.devices
            the device of the interfaces
        ip_address : str or nautobot.ipam.-addresses
            the IP address to assign
        """
        if isinstance(device, str):
            # get nautobot object of device
            nb_device = self._nautobot.dcim.devices.get(name=device)
        else:
            nb_device = device

        if isinstance(address, str):
            # get nautobot object of device
            nb_addr = self._nautobot.ipam.ip_addresses.get(
                address=address,
                namespace=namespace)
        else:
            nb_addr = address

        try:
            return nb_device.update({'primary_ip4': nb_addr.id})
        except Exception:
            logger.error(f'could not set primary IPv4 on {nb_device}')
            return False

    def assign_vrf_to_device(self, device, vrf) -> bool:
        """
        assign vrf to device
        """
        logger.debug(f'assigning vrf {vrf} to device {device}')
        if isinstance(device, str):
            # get nautobot object of device
            nb_device = self._nautobot.dcim.devices.get(name=device)
        else:
            nb_device = device
    
        properties = {'vrf': vrf,
                      'device': nb_device.id
                     }
        try:
            assignment = self._nautobot.ipam.vrf_device_assignments.create(properties)
            if assignment:
                logger.debug(f'vrf assigned to device {nb_device.display}')
            else:
                logger.error(f'failed to assign vrf {vrf} to device {nb_device.display}')
            return assignment
        except Exception as exc:
            if 'The fields device, vrf must make a unique set.' in str(exc):
                logger.debug('this VRF is already assigned')
                return True
            else:
                logger.error(f'failed to assign vrf {vrf} to device {nb_device.display}')
                raise(exc)

    def _get_interface_of_device(self, interface, device):
        """returns interface of device

        Parameters
        ----------
        device : str or nautobot.dcim.devices
            the device of the interfaces
        interface : str or nautobot.dcim.interfaces
            interface to assign IP to

        Returns
        -------
        nautobot.dcim.interfaces
            interface object

        Raises
        ------
        UnknownDeviceError
            Raises UnknownDeviceError if device is unknown
        UnknownInterfaceError
            Raises UnknownInterfaceError if interface is unknown

        """
        if isinstance(interface, str):
            # we need the device to get the interface
            if isinstance(device, str):
                # get nautobot object of device
                nb_device = self._nautobot.dcim.devices.get(name=device)
            else:
                nb_device = device

            if not nb_device:
                logger.error(f'failed to get device {device}')
                raise veritas_exceptions.UnknownDeviceError(f'failed to get device {device}')

            # get nautobot object of interface
            nb_interface = self._nautobot.dcim.interfaces.get(
                device_id=nb_device.id, 
                name=interface)
            if not nb_interface:
                logger.error(f'failed to get interface {interface}')
                raise veritas_exceptions.UnknownInterfaceError(f'failed to get interface {interface}')
        else:
            nb_interface = interface

        return nb_interface

