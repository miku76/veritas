from loguru import logger
from veritas.tools import tools


class Updater(object):
    """Generic class to update any properties in nautobot.

    Parameters
    ----------
    sot : Sot
        the sot object to use
    """
    def __init__(self, sot):
        self._instance = None
        self._sot = sot
        self._nautobot = self._sot.open_nautobot()
        self._endpoints = {'sites': self._nautobot.dcim.sites,
                           'manufacturers': self._nautobot.dcim.manufacturers,
                           'platforms': self._nautobot.dcim.platforms,
                           'devices': self._nautobot.dcim.devices,
                           'device_roles': self._nautobot.dcim.device_roles,
                           'prefixes': self._nautobot.ipam.prefixes,
                           'location_types': self._nautobot.dcim.location_types,
                           'locations': self._nautobot.dcim.locations,
                           'interface_templates': self._nautobot.dcim.interface_templates,
                           'tags': self._nautobot.extras.tags,
                           'custom_fields': self._nautobot.extras.custom_fields,
                           'custom_field_choices': self._nautobot.extras.custom_field_choices,
                           'webhooks': self._nautobot.extras.webhooks,
                           'device_types': self._nautobot.dcim.device_types,
                           'console_port_templates': self._nautobot.dcim.console_port_templates,
                           'power_port_templates': self._nautobot.dcim.power_port_templates,
                           'device_bay_templates': self._nautobot.dcim.device_bay_templates, }

    def update(self, endpoint:str, values:dict, getter:dict):
        """update entity in sot

        Parameters
        ----------
        endpoint : str
            name of the endpoint to use
        values : dict
            values to update
        getter : dict
            getter to use to check if entity is already in sot

        Returns
        -------
        entity : object
            the entity that was updated
        """
        # check if entity is already in sot
        try:
            endpoint_func = self._endpoints.get(endpoint, None)
            entity = endpoint_func.get(**getter)
            if entity is None:
                logger.debug('entity not found in sot')
                return None
        except Exception as exc:
            logger.error(f'could not get entity; got exception {exc}')
            return None

        try:
            success = entity.update(values)
            if success:
                logger.debug("entity updated in sot")
            else:
                logger.debug("entity not updated in sot")
            return entity
        except Exception as exc:
            logger.error("entity not updated in sot; got exception %s" % exc)
            return None

        return entity

    def update_by_id(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        id = properties.get('id')
        del properties['id']
        return self._nautobot.dcim.devices.update(id=id, data=properties)
