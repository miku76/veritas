from abc import ABC, abstractmethod


class BusinessLogic_Interface(ABC):
    @abstractmethod
    def __init__(self, device_properties, configparser):
        pass

    @abstractmethod
    def post_processing(self, interfaces):
        return interfaces
