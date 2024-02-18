from abc import ABC, abstractmethod

class AbstractDeviceManagement(ABC):
    # see also veritas/src/veritas/devicemanagement/scrapli.py
    
    @abstractmethod
    def __init__(self, ip, username, password, platform='ios', ssh_keyfile=None, port=22, manufacturer='cisco', scrapli_loglevel='none'):
        pass

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def get_facts(self):
        pass

    @abstractmethod
    def get_config(self, source):
        pass

