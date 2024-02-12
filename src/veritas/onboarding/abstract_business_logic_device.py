from abc import ABC, abstractmethod


class BusinessLogic_Device(ABC):
    @abstractmethod
    def __init__(self, configparser, device_fcats):
        pass

    @abstractmethod
    def pre_processing(sot, device_defaults):
        pass

    @abstractmethod
    def post_processing(sot, device_properties):
        pass
