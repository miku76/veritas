from loguru import logger


class Plugin(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.bind(extra='plugins').debug('creating onboarding registry')
            cls._instance = super(Plugin, cls).__new__(cls)
            # Initialization registry
            cls._configparser = {}
            cls._config_and_facts = {}
            cls._device_properties = {}
            cls._interface_properties= {}
            cls._vlan_properties = {}
            cls._business_logic_device = {}
            cls._business_logic_interface = {}
            cls._business_logic_config_context = {}
            cls._offline_importer = None
        return cls._instance

    def get_configparser(self, platform):
        return self._configparser.get(platform)

    def get_config_and_facts(self, platform):
        return self._config_and_facts.get(platform)

    def get_device_properties(self, platform):
        return self._device_properties.get(platform)

    def get_interface_properties(self, platform):
        return self._interface_properties.get(platform)

    def get_vlan_properties(self, platform):
        return self._vlan_properties.get(platform)

    def get_business_logic_device(self, platform):
        return self._business_logic_device.get(platform)

    def get_business_logic_interface(self, platform):
        return self._business_logic_interface.get(platform)

    def get_business_logic_config_context(self, platform):
        return self._business_logic_config_context.get(platform)

    def get_offline_importer(self):
        return self._offline_importer

    def register_configparser(self, platform, method):
        self._configparser[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered configparser for platform {platform}')

    def register_config_and_facts(self, platform, method):
        self._config_and_facts[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered config_and_facts for platform {platform}')

    def register_device_properties(self, platform, method):
        self._device_properties[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered device_properties for platform {platform}')

    def register_interface_properties(self, platform, method):
        self._interface_properties[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered interface_properties for platform {platform}')

    def register_vlan_properties(self, platform, method):
        self._vlan_properties[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered vlan_properties for platform {platform}')

    def register_business_logic_device(self, platform, method):
        self._business_logic_device[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered business logic (device) for platform {platform}')

    def register_business_logic_interface(self, platform, method):
        self._business_logic_interface[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered business logic (interface) for platform {platform}')

    def register_business_logic_config_context(self, platform, method):
        self._business_logic_config_context[platform] = method
        logger.bind(extra='plugins').debug(f'successfully registered business logic (config context) for platform {platform}')

    def register_offline_importer(self, method):
        self._offline_importer = method
        logger.bind(extra='plugins').debug('successfully registered offline importer')

def configparser(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_configparser(platform, func)
        # return fn unmodified
        return func
    return decorator

def config_and_facts(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_config_and_facts(platform, func)
        # return fn unmodified
        return func
    return decorator

def device_properties(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_device_properties(platform, func)
        # return fn unmodified
        return func
    return decorator

def interface_properties(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_interface_properties(platform, func)
        # return fn unmodified
        return func
    return decorator

def vlan_properties(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_vlan_properties(platform, func)
        # return fn unmodified
        return func
    return decorator

def device_business_logic(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_business_logic_device(platform, func)
        # return fn unmodified
        return func
    return decorator

def interface_business_logic(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_business_logic_interface(platform, func)
        # return fn unmodified
        return func
    return decorator

def config_context_business_logic(platform):
    def decorator(func):
        plugin = Plugin()
        plugin.register_business_logic_config_context(platform, func)
        # return fn unmodified
        return func
    return decorator

def offline_importer(func):
    plugin = Plugin()
    plugin.register_offline_importer(func)
    return func
