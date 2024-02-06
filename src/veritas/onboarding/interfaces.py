from ipaddress import IPv4Network
from loguru import logger


def get_interface_properties(device_defaults, ciscoconf):
    """return interface properties of ALL interfaces"""
    list_of_interfaces = []
    for name in ciscoconf.get_interfaces():
        logger.debug(f'geting property of interface {name}')
        props = get_properties(device_defaults,
                               ciscoconf,
                               name)

        list_of_interfaces.append(props)

    return list_of_interfaces

def get_properties(device_defaults, ciscoconf, name):
    """return all properties of a single interface"""

    # get interface
    interface = ciscoconf.get_interfaces().get(name)
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

    # check if interface is lag
    if 'channel_group' in interface:
        pc = "%s%s" % (ciscoconf.get_name("port-channel"), interface.get('channel_group'))
        # logger.debug(f'interface {name} is part of port-channel {pc}')
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

def get_vlan_properties(ciscoconf, device_defaults):
    global_vlans, svi, trunk_vlans = ciscoconf.get_vlans()
    list_of_vlans = []
    all_vlans = {}
    location = device_defaults['location']

    for vlan in global_vlans:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': location})

    for vlan in svi:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': device_defaults['location']})

    for vlan in trunk_vlans:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': device_defaults['location']})

    return list_of_vlans

def get_primary_interface(list_of_interfaces, configparser):
    """return IP of primary interface depending on the list of interfaces
       configured in our conboarding_config"""

    for iface in list_of_interfaces:
        if configparser.get_ipaddress(iface) is not None:
            return configparser.get_ipaddress(iface)
        else:
            logger.debug(f'no ip address on {iface} found')

    return None

def get_primary_interface_by_address(primary_address, ciscoconf):
    primary_interface = {}
    interface_name = ciscoconf.get_interface_name_by_address(primary_address)
    interface = ciscoconf.get_interface(interface_name)

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
