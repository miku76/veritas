from abc import ABC, abstractmethod


class Interface(ABC):
    @abstractmethod
    def __init__(self, configparser):
        pass

    @abstractmethod
    def get_interface_properties(self, device_defaults):
        pass
