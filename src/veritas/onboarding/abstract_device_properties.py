from abc import ABC, abstractmethod

class Device(ABC):
    @abstractmethod
    def __init__(self, sot, device_facts, configparser, onboarding_config):
        pass

    @abstractmethod
    def get_device_properties(self, device_properties):
        pass
