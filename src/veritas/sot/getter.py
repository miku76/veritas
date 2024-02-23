from loguru import logger

# veritas
from veritas.tools import tools
from veritas.sot import queries


class Getter(object):

    def __init__(self, sot):
        self._instance = None
        self._sot = sot
        self._nautobot = self._sot.open_nautobot()

    # -----===== user command =====-----

    def nautobot(self):
        return self._nautobot

    def device(self, name, by_id=False):
        """return device by using its name or id"""
        # name can be either the name (in most cases) or the id

        if by_id:
            return self._nautobot.dcim.devices.get(id=name)
        else:
            return self._nautobot.dcim.devices.get(name=name)

    def device_by_ip(self, ip, cast=False):
        """return device by using its primary IP"""
        interfaces = self.query(select=['interfaces'], 
                                using='nb.ipaddresses',
                                where={'address': ip}, 
                                mode='sql')

        if interfaces and len(interfaces) > 0 and len(interfaces[0].get('interfaces', [])) > 0:
            device = interfaces[0].get('interfaces', {})[0].get('device',{}).get('name')
            logger.debug(f'found device in sot; device={device}')
            if cast:
                return device
            else:
                return self._nautobot.dcim.devices.get(name=device)
        return None

    def primary_ip4(self, name, cast=False):
        """return primary IP4 of the device"""
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip4.display
        else:
            return device.primary_ip4

    def primary_ip6(self, name, cast=False):
        """return primary IP6 of the device"""
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip6.display
        else:
            return device.primary_ip6

    def address(self, address, by_id=False):
        """return address by using its address or id"""
        # name can be either the name (in most cases) or the id

        if by_id:
            return self._nautobot.ipam.ip_addresses.get(id=address)
        else:
            return self._nautobot.ipam.ip_addresses.get(address=address)

    def interface(self, device, interface_name, device_id=None):
        """returns interface of device"""
        # properties = tools.convert_arguments_to_properties(unnamed, named)

        # device = properties.get('device')
        # device_id = properties.get('device_id')
        # interface_name = properties.get('name')

        if device_id:
            logger.debug(f'getting Interface {interface_name} of {device_id}')
            return self._nautobot.dcim.interfaces.get(device_id=device_id, 
                                                      name=interface_name)
        else:
            logger.debug(f'getting Interface {interface_name} of {device}')
            return self._nautobot.dcim.interfaces.get(device={'name': device}, 
                                                      name=interface_name)

    def interfaces(self, *unnamed, **named):
        """return ALL interfaces of device"""
        properties = tools.convert_arguments_to_properties(unnamed, named)

        device = properties.get('device')
        device_id = properties.get('device_id')

        if device_id:
            logger.debug(f'getting ALL Interface of ID {device_id}')
            return self._nautobot.dcim.interfaces.filter(device_id=device_id)
        else:
            logger.debug(f'getting ALL Interface of {device}')
            return self._nautobot.dcim.interfaces.filter(device=device)

    def vlans(self,  *unnamed, **named):
        return self._sot.ipam.get_vlans(*unnamed, **named)

    def hldm(self, device, get_id=True):
                # select ALL possible values
        select = ['asset_tag', 'custom_fields', 'config_context', 'device_bays',
                  'device_type','interfaces' , 'local_config_context_data', 
                  'location' , 'name', 'parent_bay', 'primary_ip4',
                  'platform', 'position', 'rack' , 'role', 'serial', 'status',
                  'tags', 'tenant']

        if get_id:
            select.append('id')

        using = 'nb.devices'
        where = {'name': device}
        return self.query(select=select, using=using, where=where)
    
    def changes(self, *unnamed, **named):
        pass

    def all_custom_fields_type(self, get_list=False):
        """return list of all custom_fields_type"""

        response = {}
        cf_types = self._nautobot.extras.custom_fields.all()
        if get_list:
            return [str(t.type) for t in cf_types ]
        else:
            for t in cf_types:
                response[t.display] = {'type': str(t.type)}
            return response

    def all_device_types(self, get_list=False):
        response = {}
        device_types = self._nautobot.dcim.device_types.all()
        if get_list:
            return [t.model for t in device_types ]
        else:
            for t in device_types:
                response[t.display] = {'model': t.model}
            return response

    def get_all_roles(self, get_list=False):
        response = {}
        roles = self._nautobot.extras.roles.all()
        if get_list:
            return [r.name for r in roles ]
        else:
            for r in roles:
                response[r.display] = {'name': r.name, 'content_types': r.content_types}
            return response

    def all_platforms(self, get_list=False):
        response = {}
        platforms = self._nautobot.dcim.platforms.all()
        if get_list:
            return [p.name for p in platforms ]
        else:
            for p in platforms:
                response[p.display] = {'name': p.name}
            return response

    def all_locations(self, location_type=None, get_list=False):
        response = {}
        locations = self._nautobot.dcim.locations.all()
        if get_list:
            return [loc.name for loc in locations if loc.location_type.name == location_type or not location_type]
        else:
            for loc in locations:
                if loc.location_type.name == location_type or not location_type:
                    row = {'name': loc.name, 
                                        'location_type': loc.location_type.name,
                                        'description': loc.description,
                          }
                    if loc and loc.parent and loc.parent.name:
                        row.update({'parent': loc.parent.name})
                    else:
                        row.update({'parent': None})
                    response[loc.name] = row
            return response

    def query(self, select, using, where, mode='sql', transform=[]):
        logger.bind(extra="query").debug(f'query select {select} using {using} where {where} (query)')
        if mode == "sql":
            return queries._execute_sql_query(self, select=select, using=using, where=where, transform=transform)
        else:
            return queries._execute_gql_query(self, select=select, using=using, where=where)

    def get_ipam_choices(self):
        return self._nautobot.ipam.ip_addresses.choices()

    def get_interface_type_choices(self):
        return self._nautobot.dcim.interfaces.choices()

    # -----===== internals =====-----

