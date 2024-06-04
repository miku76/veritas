import yaml
from loguru import logger
from veritas.tools import tools


class Importer(object):

    def __init__(self, sot):
        self._sot = sot
        self._nautobot = self._sot.open_nautobot()

        self._endpoints = {'manufacturers': self._nautobot.dcim.manufacturers,
                           'platforms': self._nautobot.dcim.platforms,
                           'devices': self._nautobot.dcim.devices,
                           'racks': self._nautobot.dcim.racks,
                           'roles': self._nautobot.extras.roles,
                           'prefixes': self._nautobot.ipam.prefixes,
                           'location_types': self._nautobot.dcim.location_types,
                           'locations': self._nautobot.dcim.locations,
                           'interface_templates': self._nautobot.dcim.interface_templates,
                           'tags': self._nautobot.extras.tags,
                           'custom_fields': self._nautobot.extras.custom_fields,
                           'custom_field_choices': self._nautobot.extras.custom_field_choices,
                           'custom_links': self._nautobot.extras.custom_links,
                           'webhooks': self._nautobot.extras.webhooks,
                           'device_types': self._nautobot.dcim.device_types,
                           'console_port_templates': self._nautobot.dcim.console_port_templates,
                           'power_port_templates': self._nautobot.dcim.power_port_templates,
                           'device_bay_templates': self._nautobot.dcim.device_bay_templates,
                           }

    def __getattr__(self, item):
        if item == "xxx":
            return self

    # -----===== internals =====----- 

    def add_entity(self, func, properties):
        try:
            item = func.create(properties)
            if item:
                logger.debug("entity added to sot")
            else:
                logger.debug("entity not added to sot")
            return item
        except Exception as exc:
            logger.error("entity not added to sot; got exception %s" % exc)
            logger.error(f'properties: {properties}')
            raise(exc)

    def open_file(self, filename):
        logger.debug(f'opening file {filename}')
        with open(filename) as f:
            try:
                content = yaml.safe_load(f.read())
            except Exception as exc:
                logger.error("could not read file %s; got exception %s" % (filename, exc))
                return None
        return content

    def import_data(self, data, title, creator, bulk=False):
        success = False
        if bulk:
            success = self.add_entity(creator, data)
            if success:
                logger.debug(f'{title} successfully added to sot')
            else:
                logger.error(f'could not add {title} to sot')
        else:
            for item in data:
                success = self.add_entity(creator, item)
                if success:
                    logger.debug(f'{title} successfully added to sot')
                else:
                    logger.error(f'could not add {title} to sot')
        return success

    # -----===== user commands =====----- 

    def add(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        endpoint = properties.get('endpoint')
        if not endpoint:
            logger.error('please specify endpoint')
            return False
        bulk=properties.get('bulk', False)

        if 'file' in properties:
            content = self.open_file(properties['file'])
            return self.import_data(content['interface_templates'], endpoint, self._endpoints[endpoint])
        elif 'properties' in properties:
            return self.import_data(properties['properties'], endpoint, self._endpoints[endpoint], bulk=bulk)
