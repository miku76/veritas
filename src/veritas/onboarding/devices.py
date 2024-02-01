import sys
from loguru import logger
from datetime import datetime
from slugify import slugify
from deepmerge import always_merger
from benedict import benedict

# veritas
from . import additional as additional


def get_device_properties(sot, device_properties, device_facts, ciscoconf, onboarding_config):

    # if the device model was set in device_facts we use this value instead of the default value
    device_properties['device_type'] = device_facts.get('device_type', device_facts.get('model'))

    # check if serial_number is list or string. We need {'12345','12345'}
    if 'serial' not in device_properties:
        if isinstance(device_facts.get("serial_number"), list):
            sn = ', '.join(map(str, device_facts["serial_number"]))
        else:
            sn = device_facts.get("serial_number")
    
        device_properties['serial'] = sn
        logger.bind(extra='gdp (+)').trace(f'key=serial value={sn}')

    # set custom fields; slugify value
    cf_fields = benedict(keyattr_dynamic=True)
    for key, value in device_properties.get('custom_fields',{}).items():
        if value is not None:
            cf_fields[key.lower()] = slugify(value)

    # slugify device_type
    if 'device_type' in device_properties:
        device_properties['device_type'] = slugify(device_properties['device_type'])
        logger.bind(extra='gdp (=)').trace(
            f'key=device_type value={device_properties["device_type"]}'
        )

    # set current time
    now = datetime.now()
    current_time = now.strftime('%Y-%m-%d %H:%M:%S')
    cf_fields.update({'last_modified': current_time})

    try:
        # add user defined additional values
        logger.info('getting additional values')
        additional_values = additional.additional(device_properties,
                                                  device_facts,
                                                  ciscoconf,
                                                  onboarding_config)
        saved_tags = device_properties.get('tags',[])
        for key,value in dict(additional_values).items():
            if key.startswith('cf_'):
                k = key.split('cf_')[1]
                cf_fields[k] = value
                del additional_values[key]
                logger.bind(extra='add (=)').trace(f'key={key} value={value}')
            elif key == 'tags':
                if isinstance(value, str):
                    saved_tags.append(value)
                else:
                    saved_tags = saved_tags + value
            else:
                if key in device_properties:
                    logger.bind(extra='add (=)').trace(f'key={key} value={value}')

        # merge the device properties and the additional values
        # this merge is destructive!!!
        result = always_merger.merge(device_properties, additional_values)
        # restore tags!
        if len(saved_tags) > 0:
            result['tags'] = saved_tags
        device_properties = result
        device_properties.update({'custom_fields': cf_fields})

        # for key,value in additional_values.items():
        #     logger.debug(f'updating device_properties {key}={value} (additional value)')
        #     if key == 'primary_ip' and len(value) > 0:
        #         primary_address = value
        #         primary_interface_name = ciscoconf.get_interface_name_by_address(primary_address)
        #         new_primary_interface = ciscoconf.get_interface(primary_interface_name)
        #         # we need the name of the interface
        #         if 'name' not in new_primary_interface:
        #             new_primary_interface['name'] = primary_interface_name
        #         if new_primary_interface:
        #             logger.info(f'change primary_ip to {primary_address} and interface {primary_interface_name}')
        #             device_properties['primary_interface'] = new_primary_interface
        #             logger.bind(extra='add (=)').trace(f'key=primary_interface value={new_primary_interface}')
        #     elif key.startswith('cf_'):
        #         k = key.split('cf_')[1]
        #         cf_fields[k] = value
        #     else:
        #         device_properties[key] = value
        #         logger.bind(extra='add (=)').trace(f'key={key} value={value}')
        # add custom fields to device properties
        # device_properties.update({'custom_fields': cf_fields})
        # logger.bind(extra='add (=)').trace(f'key=custom_fields value={cf_fields}')
    except Exception as exc:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("device properties failed in line %s; got: %s (%s, %s, %s)" % (exc_tb.tb_lineno,
                                                                                    exc,
                                                                                    exc_type,
                                                                                    exc_obj,
                                                                                    exc_tb))
        logger.error(f'device_properties: {device_properties}')
        # remove ALL device_properties to signal that something failed
        device_properties = None
        return None
