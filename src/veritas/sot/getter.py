from loguru import logger
from veritas.tools import tools


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

    def query(self, select, using, where, mode='sql', reformat=None):
        logger.bind(extra="query").debug(f'query select {select} using {using} where {where} (query)')
        if mode == "sql":
            return self._execute_sql_query(select=select, using=using, where=where, reformat=reformat)
        else:
            return self._execute_gql_query(select=select, using=using, where=where)

    def get_ipam_choices(self):
        return self._nautobot.ipam.ip_addresses.choices()

    def get_interface_type_choices(self):
        return self._nautobot.dcim.interfaces.choices()

    # -----===== internals =====-----

    def _execute_sql_query(self, select:str, using:str, where:str, reformat: str=None) -> dict:
        """execute sql like query and return data"""

        self._nautobot = self._sot.open_nautobot()

        subqueries = {'__interfaces_params__': [],
                      '__interface_assignments_params__': [],
                      '__primaryip4for_params__': [],
                      '__devices_params__': [],
                      '__prefixes_params__': [],
                      '__changes_params__': [],
                      '__ipaddresses_params__': [],
                      '__vlans_params__': [],
                      '__locations_params__': [],
                      '__tags_params__': [],
                      '__general_params__': [],
                      '__vms_params__': []}

        # read query from config
        query = self._sot.sot_config.get('queries',{}).get(using)

        if 'ipaddress_to_device' == reformat and 'primary_ip4_for' not in select:
            logger.warning('reformatting ipaddress_to_device needs primary_ip4_for')
            select.append('primary_ip4_for')

        # get final variables for our main parameter
        query_final_vars, cf_fields_types = self._dict_to_query_var(where, "")

        # loop through where statement and put values to subqueries and adjust custom field types
        for whr in where:
            #
            # we have some special cases
            # some queries have the possibility of "sub" queries eg. when you want to poll
            # devices within a specific prefix range that belong to a specific platform
            # primary_ip4_for(__primaryip4for_params__) is used to query for the platform
            #
            # the syntax to use the subqueries is:
            # devices = sot.select('id, hostname, primary_ip4_for') \
            #              .using('nb.ipaddresses') \
            #              .where('prefix="192.168.0.0/24" and pip4for_cf_net=eins')
            if whr.startswith('interfaces_'):
                subqueries['__interfaces_params__'].append(f'{whr.replace("interfaces_","")}: ${whr}')
            elif whr.startswith('pip4for_'):
                subqueries['__primaryip4for_params__'].append(f'{whr.replace("pip4for_","")}: ${whr}')
            elif whr.startswith('assignments_'):
                subqueries['__interface_assignments_params__'].append(f'{whr.replace("assignments_","")}: ${whr}')
            else:
                sq = f'__{using.replace("nb.","")}_params__'
                subqueries[sq].append(f'{whr}: ${whr}')

            # adjust the type of custom fields
            name = f'${whr}: String'
            if isinstance(where[whr], list) and name in query_final_vars:
                logger.debug(f'convert {whr} to String')
                where[whr] = where[whr][0]

        # convert string ["val1","val2",....,"valn"] to list
        for key,val in dict(where).items():
            logger.bind(extra="cnvt whr").trace(f'key: {key} val: {val} type(val): {type(val)}')
            if isinstance(val, str):
                if val.startswith('"') and val.endswith('"'):
                    logger.warning(f'val {val} is encapsulated with a ".." this may cause problems')
                # convert Boolean to True/False
                if cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Boolean (true/false)':
                    logger.bind(extra="cnvt whr").trace(f'converting val: {val} to bool')
                    if 'true' in val.lower():
                        where[key] = True
                    else:
                        where[key] = False
            elif isinstance(val, list):
                logger.warning('todo(???) .... cast list???')
                # this is the only place where we can convert a list to a string
                # keys like prefix or within_include require a string
                #
                # when we use **boolean expressions** we get the where values as LIST (!!)
                #
                # in this case we convert the list to a string
                #
                # when we use **simple queries** we get the values as STRING (!!!)
                # 
                # if key in ['within_include', 'changed_object_type', 'prefix']:
                #     logger.bind(extra="cnvt whr").trace(f'converting val: {val} - within_include')
                #     where[key] = val[0]
                # # when using custom fields we have to convert the values as well
                # elif cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Text':
                #     if len(val) > 1:
                #         logger.erro(f'parameter {key} does not support [String]')
                #     logger.bind(extra="cnvt whr").trace(f'converting val: {val} - cf_fields is Text')
                #     where[key] = val[0]
                # elif cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Boolean (true/false)':
                #     logger.bind(extra="cnvt whr").trace(f'converting val: {val} - cf_fields is bool')
                #     if 'true' in val[0].lower():
                #         where[key] = True
                #     else:
                #         where[key] = False

        str_final_vars = ",".join(query_final_vars)
        # the query variables
        query = query.replace('__query_vars__', str_final_vars)                     
        for q in subqueries:
            query = query.replace(q, ",".join(subqueries[q]))
        # cleanup
        query = query.replace('{}','').replace('()','')

        # select are values the user has SELECTed
        for v in select:
            if v.startswith('cf_'):
                where['get_custom_field_data'] = True
            else:
                where[f'get_{v}'] = True

        # debugging output
        logger.bind(extra="query").trace('--- query_vars ---')
        logger.bind(extra="query").trace(str_final_vars)
        for q in subqueries:
            logger.bind(extra="query").trace(q)
            logger.bind(extra="query").trace(subqueries[q])
        logger.bind(extra="query").trace('--- query ---')
        logger.bind(extra="query").trace(query)
        logger.bind(extra="query").trace('--- select ---')
        logger.bind(extra="query").trace(select)
        logger.bind(extra="query").trace('--- where ---')
        logger.bind(extra="query").trace(where)

        response = None
        logger.debug(f'select={select} using={using} where={where}')
        with logger.catch():
            response = self._nautobot.graphql.query(query=query, variables=where).json
        if not response:
            logger.error('got no valid response')
            return {}
        # logger.debug(response)

        if reformat:
            logger.debug(f'reformating response; reformat={reformat}')
            if 'ipaddress_to_device' == reformat:
                raw_data = dict(response)['data']['ip_addresses']
                data = []
                for device in raw_data:
                    primary_ip4_for = device.get('primary_ip4_for')
                    data.append(primary_ip4_for[0])
        elif 'errors' in response:
            logger.error(f'got error: {response.get("errors")}')
            response = {}
        elif 'nb.ipaddresses' in using:
            data = dict(response)['data']['ip_addresses']
        elif 'nb.vlan' in using:
            data = dict(response)['data']['vlans']
        elif 'nb.prefixes' in using:
            data = dict(response)['data']['prefixes']
        elif 'nb.general' in using:
            data = dict(response)['data']
        elif 'nb.changes' in using:
            data = dict(response)['data']['object_changes']
        elif 'nb.vms' in using:
            data = dict(response)['data']['virtual_machines']
        else:
            data = dict(response).get('data',{}).get('devices',{})
        return data

    def _execute_gql_query(self, *unnamed, **named):
        """execute GraphQL based queries"""

        variables = {}
        query_final_vars = []

        subqueries = {'__interfaces_params__': [],
                      '__interfaces_assignments_params__': [],
                      '__primaryip4for_params__': [],
                      '__devices_params__': [],
                      '__prefixes_params__': [],
                      '__changes_params__': [],
                      '__ipaddresses_params__': [],
                      '__vlans_params__': [],
                      '__locations_params__': [],
                      '__tags_params__': [],
                      '__general_params__': [],
                      '__vms_params__': []}

        properties = tools.convert_arguments_to_properties(unnamed, named)        
        select = properties.get('select',{})
        using = properties.get('using', 'nb.devices')
        where = properties.get('where', {})
        query = self._sot.sot_config.get('queries',{}).get(using)

        for sq in where:
            prefix = f'{sq}_' if sq != 'devices' else ""
            qfv, cf_fields_types = self._dict_to_query_var(where[sq], prefix)
            query_final_vars += qfv
            sq_name = f'__{sq}_params__'
            for key,value in where[sq].items():
                subqueries[sq_name].append(f'{key}: ${prefix}{key}')
                variables[f'{prefix}{key}'] = value

        # select are values the user has SELECTed
        for v in select:
            if v.startswith('cf_'):
                variables['get__custom_field_data'] = True
            else:
                variables[f'get_{v}'] = True
        
        str_final_vars = ",".join(query_final_vars)
        # the query variables
        query = query.replace('__query_vars__', str_final_vars)                     
        for q in subqueries:
            query = query.replace(q, ",".join(subqueries[q]))
        # cleanup
        query = query.replace('{}','').replace('()','')

        # debugging output
        # print('--- str_final_vars ---')
        # print(str_final_vars)
        # for q in subqueries:
        #     print(q)
        #     print(subqueries[q])
        # print('--- query ---')
        # print(query)
        # print('--- variables ---')
        # print(variables)

        response = self._nautobot.graphql.query(query=query, variables=variables).json
        # logger.debug(response)
        if 'errors' in response:
            logger.error(f'got error: {response.get("errors")}')
            response = {}
        if 'nb.ipaddresses' in using:
            data = dict(response)['data']['ip_addresses']
        elif 'nb.vlan' in using:
            data = dict(response)['data']['vlans']
        elif 'nb.prefixes' in using:
            data = dict(response)['data']['prefixes']
        elif 'nb.general' in using:
            data = dict(response)['data']
        elif 'nb.changes' in using:
            data = dict(response)['data']['object_changes']
        else:
            data = dict(response).get('data',{}).get('devices',{})
        return data

    def _dict_to_query_var(self, data, prefix):
        """return list containing name of paramter and type of cf field types"""
        logger.bind(extra="query_var").debug('_dict_to_query_var')
        response = []
        cf_fields_types = None

        for whr in dict(data):
            # custom fields are a special case
            # we do NOT know what custom fields are part of the SOT
            cf_name = whr.replace('pip4for_','').replace('interfaces_','')
            if cf_name.startswith('cf_'):
                logger.bind(extra="query_var").trace('cf_name={cf_name}')
                if not cf_fields_types:
                    cf_fields_types = self.all_custom_fields_type()

                # set default value to String
                cf_type = "String"
                if cf_name.replace('cf_','') in cf_fields_types:
                    cf_type = cf_fields_types[cf_name.replace('cf_','')]['type']

                if cf_type.lower() == "text":
                    logger.bind(extra="query_var").trace(f'whr={whr} is String')
                    response.append(f'${prefix}{whr}: String')
                elif cf_type == "Boolean (true/false)":
                    logger.bind(extra="query_var").trace(f'whr={whr} is Boolean')
                    response.append(f'${prefix}{whr}: Boolean')
                else:
                    logger.bind(extra="query_var").trace(f'whr={whr} is [String]')
                    response.append(f'${prefix}{whr}: [String]')
            else:
                # we have to check within_include... is it String or [String]
                # we have to check if prefix is String or [String]
                if whr in ['changed_object_type']:
                    logger.bind(extra="query_var").trace(f'whr={whr} is String')
                    response.append(f'${prefix}{whr}: String')
                elif whr in ['vid', '']:
                    logger.bind(extra="query_var").trace(f'whr={whr} is Int')
                    response.append(f'${prefix}{whr}: [Int]')
                else:
                    logger.bind(extra="query_var").trace(f'whr={whr} is [String]')
                    response.append(f'${prefix}{whr}: [String]')
        return response, cf_fields_types
    
