from abc import ABC, abstractmethod


class BusinessLogic_ConfigContext(ABC):
    @abstractmethod
    def __init__(self, device_properties, device_facts, interfaces, configparser):
        pass

    @abstractmethod
    def post_processing(self, config_context):
        pass
