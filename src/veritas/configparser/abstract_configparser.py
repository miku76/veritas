from abc import ABC, abstractmethod


class Configparser(ABC):
    """abstract class to implement a configparser for different platforms

    Parameters
    ----------
    config : list
        device configuration
    platform : str
        platform of the device
    """
    @abstractmethod
    def __init__(self, config, platform):
        pass

    @abstractmethod
    def get_interface_ipaddress(self, interface:str) -> dict:
        """get interface IP address

        Parameters
        ----------
        interface : str
            name of the interface

        Returns
        -------
        interface : dict
            interface configuration
        """   
        pass

    @abstractmethod
    def get_interface_name_by_address(self, address:str) -> str | None:
        """get interface name by IP address

        Parameters
        ----------
        address : str
            IP address

        Returns
        -------
        interface_name : str | None
            interface name
        """
        pass

    @abstractmethod
    def get_interfaces(self) -> dict:
        """get interfaces

        Returns
        -------
        interfaces : dict
            interfaces
        """
        pass

    @abstractmethod
    def find_in_global(self, properties:dict) -> bool:
        """check if properties are found in global config

        Parameters
        ----------
        properties : dict
            properties to search for

        Returns
        -------
        found : bool
            True if found, False otherwise
        """
        pass

    @abstractmethod
    def find_in_interfaces(self, properties:dict) -> list:
        """return list of interfaces that match properties

        Parameters
        ----------
        properties : dict
            properties to search for

        Returns
        -------
        interfaces : list
            list of interfaces that match properties
        """
        pass

    @abstractmethod
    def get_fqdn(self) -> str:
        """return FQDN of device

        Returns
        -------
        fqdn : str
            fqdn of device
        """       
        pass
