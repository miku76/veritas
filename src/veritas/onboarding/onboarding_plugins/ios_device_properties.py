import sys
from loguru import logger
from datetime import datetime
from slugify import slugify
from deepmerge import always_merger
from benedict import benedict

# veritas
from veritas.onboarding import plugins
from veritas.onboarding import additional
from veritas.onboarding import abstract_device_properties as abc_device


class DeviceProperties(abc_device.Device):
    def __init__(self, sot, device_facts, configparser, onboarding_config):
        logger.debug('initialiting DeviceProperties object')
        self._sot = sot
        self._device_facts = device_facts
        self._configparser = configparser
        self._onboarding_config = onboarding_config

    def get_device_properties(self, device_properties):
        # if the device model was set in device_facts we use this value instead of the default value
        device_properties['device_type'] = self._device_facts.get('device_type', self._device_facts.get('model'))

        # check if serial_number is list or string. We need {'12345','12345'}
        if 'serial' not in device_properties:
            if isinstance(self._device_facts.get("serial_number"), list):
                sn = ', '.join(map(str, self._device_facts["serial_number"]))
            else:
                sn = self._device_facts.get("serial_number")
        
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
                                                      self._device_facts,
                                                      self._configparser,
                                                      self._onboarding_config)
            # we have to merge all tags. So just save tags now and add new ones later
            saved_tags = device_properties.get('tags',[])
            for key,value in dict(additional_values).items():
                if key.startswith('cf_'):
                    k = key.split('cf_')[1]
                    cf_fields[k] = value
                    del additional_values[key]
                    logger.bind(extra='add (=)').trace(f'key={key} value={value}')
                elif key == 'tags':
                    # do not overwrite tags. We build a list of tags
                    if isinstance(value, str):
                        saved_tags.append(value)
                    else:
                        saved_tags = saved_tags + value
                elif key == 'primary_interface':
                    # check if we have to change the address
                    primary_address = additional_values.get('primary_interface',{}).get('address')
                    if primary_address:
                        # the primary IP has changed. Get the primary interface
                        primary_interface_name = self._configparser.get_interface_name_by_address(primary_address)
                        new_primary_interface = self._configparser.get_interface(primary_interface_name)
                        logger.info(f'change primary_ip to {primary_address} and interface to {primary_interface_name}')
                        logger.bind(extra='add (=)').\
                            trace(f'key=primary_interface.address value={primary_address}')
                        # if we found the new interface we use this value
                        # otherwise we use default values
                        if new_primary_interface:
                            additional_values['primary_interface.name'] = primary_interface_name
                            additional_values['primary_interface.description'] = new_primary_interface.get('description','')
                            additional_values['primary_interface.mask'] = new_primary_interface.get('mask','')
                            logger.bind(extra='add (=)').\
                                trace(f'key=primary_interface.name value={primary_interface_name}')
                            logger.bind(extra='add (=)').\
                                trace(f'key=primary_interface.description value={new_primary_interface.get("description","")}')
                            logger.bind(extra='add (=)').\
                                trace(f'key=primary_interface.mask value={new_primary_interface.get("mask","")}')
                else:
                    if key in device_properties:
                        logger.bind(extra='add (=)').trace(f'key={key} value={value}')

            # merge the device properties and the additional values
            # this merge is destructive!!!
            result = always_merger.merge(device_properties, dict(additional_values))
            # restore tags!
            if len(saved_tags) > 0:
                result['tags'] = saved_tags
            device_properties.update({'custom_fields': cf_fields})
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

@plugins.device_properties('ios')
def get_device_properties(sot, device_facts, configparser, onboarding_config):
    return DeviceProperties(sot, device_facts, configparser, onboarding_config)
