from loguru import logger
from importlib.metadata import version
import os

# veritas
import veritas.auth

__version__ = version("veritas")


class Profile(object):

    def __init__(self, 
        profile_config=None, profile_name=None, 
        username=None, password=None, 
        ssh_key=None, ssh_passphrase=None):
        """init Profile"""

        if profile_name is not None:
            self._username = profile_config.get('profiles',{}).get(profile_name,{}).get('username')
            username_token = profile_config.get('profiles',{}).get(profile_name,{}).get('password')
            ssh_token = profile_config.get('profiles',{}).get(profile_name,{}).get('ssh_key_passphrase')

            # decrypt user password
            if self._username and username_token:
                self._password = veritas.auth.decrypt(
                    token=username_token,
                    encryption_key=os.getenv('ENCRYPTIONKEY'), 
                    salt=os.getenv('SALT'), 
                    iterations=int(os.getenv('ITERATIONS')))
            else:
                self._password = None

            # decrypt ssh_passphrase
            if ssh_token and ssh_token.lower() != 'none':
                self._ssh_passphrase = veritas.auth.decrypt(
                    token=ssh_token,
                    encryption_key=os.getenv('ENCRYPTIONKEY'), 
                    salt=os.getenv('SALT'), 
                    iterations=int(os.getenv('ITERATIONS')))
            else:
                self._ssh_passphrase = None

        # overwrite username and password if configured by user
        self._username = username if username else self._username
        self._password = password if password else self._password
        self._ssh_key = ssh_key if ssh_key else profile_config.get('profiles',{}).get(profile_name,{}).get('ssh_key')

        logger.info(f'profile added username={self._username} password=xxx ssh_key={self._ssh_key}')
    
    @property
    def username(self) -> str:
        """return username"""       
        return self._username
    
    @property
    def password(self) -> str:
        """return password"""       
        return self._password
    
    @property
    def ssh_key(self) -> str:
        """return ssh_key"""       
        return self._ssh_key

    @property
    def ssh_passphrase(self) -> str:
        """return _sh_passphrase"""       
        return self._ssh_passphrase
