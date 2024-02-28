from abc import ABC, abstractmethod

class AbstractDeviceManagement(ABC):
    """abstract class for device management

    Parameters
    ----------
    ip : str
        ip address of the device
    username : str
        username for the device
    password : str
        password for the device
    platform : str
        platform of the device
    ssh_keyfile : str
        ssh keyfile for the device
    port : int
        port for the device
    manufacturer : str
        manufacturer of the device
    scrapli_loglevel : str
        loglevel for scrapli
    
     # see also veritas/src/veritas/devicemanagement/scrapli.py
    """    
    
    @abstractmethod
    def __init__(self, ip:str, username:str, password:str, platform:str='ios', 
                 ssh_keyfile:str=None, port:int=22, manufacturer:str='cisco', scrapli_loglevel:str='none'):
        pass

    @abstractmethod
    def open(self):
        """open connection to the device"""
        pass

    @abstractmethod
    def close(self):
        """close connection to the device"""
        pass

    @abstractmethod
    def get_facts(self):
        """get facts from the device"""
        pass

    @abstractmethod
    def get_config(self, source):
        """get config from the device"""
        pass

