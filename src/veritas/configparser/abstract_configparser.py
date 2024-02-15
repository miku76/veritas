from abc import ABC, abstractmethod


class Configparser(ABC):

    @abstractmethod
    def __init__(self, config, platform):
        pass

    @abstractmethod
    def get_interface_ipaddress(self, interface):
        pass

    @abstractmethod
    def get_interface_name_by_address(self, address):
        pass

    @abstractmethod
    def get_interface(self, interface):
        pass

    @abstractmethod
    def find_in_global(self, properties):
        pass

    @abstractmethod
    def find_in_interfaces(self, properties):
        pass

    @abstractmethod
    def get_fqdn(self):
        pass
