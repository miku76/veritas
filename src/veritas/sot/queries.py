from loguru import logger
from benedict import benedict
import pandas as pd

# veritas
from veritas.tools import tools

# these method are used to execute queries against the SOT and are private
# they are used by the public methods in the getter.py

def _execute_sql_query(getter_obj, select:str, using:str, where:str, transform: list=[]) -> dict:
    """execute sql like query and return data"""

    getter_obj._nautobot = getter_obj._sot.open_nautobot()

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
    query = getter_obj._sot.sot_config.get('queries',{}).get(using)

    if 'ipaddress_to_device' in transform and 'primary_ip4_for' not in select:
        logger.warning('transforming ipaddress_to_device needs primary_ip4_for')
        select.append('primary_ip4_for')

    # get final variables for our main parameter
    query_final_vars, cf_fields_types = _get_query_variables(getter_obj, where, "")
    logger.bind(extra="query").debug(f'query_final_vars={query_final_vars}')

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
        logger.bind(extra="cnvt where").trace(f'key: {key} val: {val} type(val): {type(val)}')
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

    # convert query_final_vars, which is a list, into a string
    str_final_vars = ",".join(query_final_vars)
    # now replace the placeholder with the query variables
    query = query.replace('__query_vars__', str_final_vars)
    # we have some subqueries, replace them                    
    for q in subqueries:
        query = query.replace(q, ",".join(subqueries[q]))
    # cleanup
    query = query.replace('{}','').replace('()','')

    # select are values the user has SELECTed
    for v in select:
        if v.startswith('cf_'):
            where['get_custom_field_data'] = True
        else:
            # we may have a . in our select values eg. platform.name
            where[f'get_{v.split(".")[0]}'] = True

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
        response = getter_obj._nautobot.graphql.query(query=query, variables=where).json
    if not response:
        logger.error('got no valid response')
        return {}

    if 'errors' in response:
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

    if transform:
        return  transform_data(data, transform, select=select)
    return data

def _execute_gql_query(getter_obj, select:list, using:str, where: dict={}) -> dict:
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

    query = getter_obj._sot.sot_config.get('queries',{}).get(using)

    for sq in where:
        prefix = f'{sq}_' if sq != 'devices' else ""
        qfv, cf_fields_types = _get_query_variables(getter_obj, where[sq], prefix)
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

    response = getter_obj._nautobot.graphql.query(query=query, variables=variables).json
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

def _get_query_variables(getter_obj, data:dict, prefix: str) -> tuple[list, dict]:
    """return list containing name of paramter and type of cf field types"""
    logger.bind(extra="query_var").debug('running _get_query_variables')
    response = []
    cf_fields_types = None

    for whr in dict(data):
        # custom fields are a special case
        # we do NOT know what custom fields are part of the SOT
        cf_name = whr.replace('pip4for_','').replace('interfaces_','')
        if cf_name.startswith('cf_'):
            logger.bind(extra="query_var").trace('cf_name={cf_name}')
            if not cf_fields_types:
                cf_fields_types = getter_obj.all_custom_fields_type()

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

# transformers (transformers do not need the getter object) 
# and are called by the getter as well as the selection (where) method when joining data

def transform_data(data: dict, transform:list, **kwargs) -> dict:
    """transform data"""
    for transformation  in transform:
        logger.debug(f'transforming data using {transformation}')
        if 'remove_id' in transformation:
            logger.debug('removing id')
            tools.remove_key_from_dict(data, 'id', key_in_str=False)

        if 'values_only' in transformation:
            values =  kwargs.get('select',[])
            data = _values_only(data, values)

        if 'to_pandas' in transformation:
            data = _to_pandas(data)

        if 'ipaddress_to_device' == transformation:
            response = []
            for device in data:
                primary_ip4_for = device.get('primary_ip4_for')
                response.append(primary_ip4_for[0])
            data = response

    return data

def _values_only(data: dict, select:list = None) -> list:
    """return only the values from a dict that are in select list"""
    response = []
    for item in data:
        dta = benedict(item, keyattr_dynamic=True)
        row = {}
        for slct in select:
            try:
                row[slct] = dta[slct]
            except KeyError:
                continue
        response.append(row)
    return response

def _to_pandas(data: list) -> pd.DataFrame:
    """convert devices to pandas dataframe"""
    my_list = []
    for item in data:
        flattened = tools.flatten_dict_with_lists(item)
        result = {}
        for key,value in flattened:
            result[key] = value
        my_list.append(result)
    
    return pd.DataFrame.from_records(my_list)
