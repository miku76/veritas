from ipaddress import IPv4Network
from loguru import logger

# veritas
from veritas.onboarding import plugins
from veritas.onboarding import abstract_interface_properties as abc_interface


class InterfaceProperties(abc_interface.Interface):
    def __init__(self, configparser):
        logger.debug('initialiting InterfaceProperties object')
        self._configparser = configparser

    def get_interface_properties(self, device_defaults):
        """return interface properties of ALL interfaces"""
        list_of_interfaces = []
        for name in self._configparser.get_interfaces():
            logger.debug(f'geting property of interface {name}')
            props = self.get_properties(device_defaults, name)

            list_of_interfaces.append(props)

        return list_of_interfaces

    def get_properties(self, device_defaults, name):
        """return all properties of a single interface"""

        # get interface
        interface = self._configparser.get_interfaces().get(name)
        # set location
        location = device_defaults['location']

        # description must not be None
        description = interface.get('description',"")
        # set the basic properties of the device
        interface_properties = {
                'name': name,
                'type': interface.get('type','1000base-t'),
                'enabled': 'shutdown' not in interface,
                'description': description,
                'status': {'name': 'Active'}
        }

        if 'port-channel' in name.lower():
            interface_properties.update({'type': 'lag'})
            logger.bind(extra='iface').trace('key=type value=lag')

        if 'ip' in interface:
            ip = interface.get("ip")
            # in case there is a / in our IP (this should not happen)
            if '/' in ip:
                cidr = interface.get('ip')
            else:
                ipv4 = IPv4Network(f'{interface.get("ip")}/{interface.get("mask")}', strict=False)
                cidr = f'{interface.get("ip")}/{ipv4.prefixlen}'
            interface_properties.update({"ip_addresses": [
                                            {"address": cidr,
                                            "status": {
                                                "name": "Active"
                                            }
                                            }
                                        ]})

        # check if interface is part of lag
        if 'channel_group' in interface:
            pc = "%s%s" % (self._configparser.get_correct_naming("port-channel"), interface.get('channel_group'))
            logger.debug(f'interface {name} is part of port-channel {pc}')
            logger.bind(extra='iface').trace(f'key=lag.name value={pc}')
            interface_properties.update({'lag': {'name': pc }})

        # setting switchport or trunk
        if 'mode' in interface:
            mode = interface.get('mode')
            data = {}
            # process access switch ports
            if mode == 'access':
                logger.debug(f'interface is access switchport {name}')
                data = {"mode": "access",
                        "untagged_vlan": {'vid': interface.get('vlan'),
                                        'location': {'name': location}
                                        }
                    }
            # process trunks
            elif mode == 'trunk':
                logger.debug(f'interface is a tagged switchport {name}')
                # this port is either a trunk with allowed vlans (mode: tagged)
                # or a trunk with all vlans mode: tagged-all
                if 'vlans_allowed' in interface:
                    vlans = []
                    for vlan in interface.get('vlans_allowed'):
                        vlans.append({'vid': vlan,
                                    'location': {'name': location}
                                    })
                    data = {'mode': 'tagged', 
                            'tagged_vlans': vlans}
                else:
                    data = {'mode': "tagged-all"}

            if len(data) > 0:
                logger.debug(f'updating interface {name}')
                interface_properties.update(data)

        return interface_properties

@plugins.interface_properties('ios')
def get_interface_properties(configparser):
    return InterfaceProperties(configparser)
