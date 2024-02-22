from loguru import logger
from importlib.metadata import version
import os

# veritas
import veritas.auth

__version__ = version("veritas")


class Profile(object):
    """This class reads the profile configuration and sets the username, password, ssh_key and ssh_passphrase.

    Parameters
    ----------
    profile_config : dict
        the profile configuration
    profile_name : str
        the profile name that should be used
    username : str
        the username that should be used
    psasword : str
        the password that should be used
    ssh_key : str  
        the ssh_key that should be used
    ssh_passphrase : str
        the ssh_passphrase that should be used
    """
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
                logger.bind(extra="profile").debug('decrypting username and token')
                self._password = veritas.auth.decrypt(
                    token=username_token,
                    encryption_key=os.getenv('ENCRYPTIONKEY'), 
                    salt=os.getenv('SALT'), 
                    iterations=int(os.getenv('ITERATIONS')))
            else:
                self._password = None

            # decrypt ssh_passphrase
            if ssh_token and ssh_token.lower() != 'none':
                logger.bind(extra="profile").debug('decrypting ssh_token')
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

        logger.bind(extra="profile").info(f'profile added username={self._username} password=xxx ssh_key={self._ssh_key}')
    
    @property
    def username(self) -> str:
        """return username

        Returns
        -------
        username : str
            the username
        """           
        return self._username
    
    @property
    def password(self) -> str:
        """return password

        Returns
        -------
        password : str
            the password
        """       
        return self._password
    
    @property
    def ssh_key(self) -> str:
        """return ssh_key

        Returns
        -------
        ssh_key : str
            the ssh_key
        """        
        return self._ssh_key

    @property
    def ssh_passphrase(self) -> str:
        """retrun ssh_passphrase

        Returns
        -------
        ssh_passphrase : str
            the ssh_passphrase
        """         
        return self._ssh_passphrase
