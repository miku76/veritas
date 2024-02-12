from loguru import logger


class Plugin(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.debug('Creating plugin object')
            cls._instance = super(Plugin, cls).__new__(cls)
            # Put any initialization here.
            cls._registry = {'kobold': {}}
        return cls._instance

    def get(self, app, name):
        return self._registry.get(app,{}).get(name)

    def get_kobold_plugin(self, name):
        return self._registry.get('kobold',{}).get(name)
    
    def get_registry(self, app):
        return self._registry.get(app)

    # internals

    def add(self, app, name, method):
        logger.debug(f'added {name} to registry')
        self._registry[app][name] = method

def kobold(name):
    def decorator(func):
        plugin = Plugin()
        logger.debug(f'registering {name} / {func}')
        plugin.add('kobold', name, func)
        # return fn unmodified
        return func
    return decorator
 