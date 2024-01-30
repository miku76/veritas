"""this module encrypts and decrypts passwords

This module is used to store passwords in encrypted form in the profile.
"""
import base64
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def encrypt(password:str, encryption_key:str, salt:str, iterations:int=400000):
    """encrypt password

    Parameters
    ----------
    password : str
        clear password
    encryption_key : str
        encryption key
    salt : str
        salt
    iterations : int, optional
        iterations, by default 400000

    Returns
    -------
    encrypted : str
        base64 encoded and encrypted password
    """
    password_bytes = str.encode(password)
    encrypt_pwd_bytes = str.encode(encryption_key)
    salt_bytes = str.encode(salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=iterations,
    )
    key = base64.urlsafe_b64encode(kdf.derive(encrypt_pwd_bytes))
    f = Fernet(key)
    token = f.encrypt(password_bytes)
    return base64.b64encode(token)

def decrypt(token:str, encryption_key:str, salt:str, iterations:int=400000):
    """decrypt token

    Parameters
    ----------
    token : str
        token (base64 encrypted password)
    encryption_key : str
        encryption key
    salt : str
        salt
    iterations : int, optional
        iterations, by default 400000

    Returns
    -------
    password : str
        clear password
    """
    token_bytes = base64.b64decode(token)
    encryption_key_bytes = str.encode(encryption_key)
    salt_bytes = str.encode(salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=iterations,
    )
    key = base64.urlsafe_b64encode(kdf.derive(encryption_key_bytes))

    f = Fernet(key)
    try:
        return f.decrypt(token_bytes).decode("utf-8")
    except Exception as exc:
        logger.debug(f'encryption_key={encryption_key} salt={salt} iterations={iterations} ')
        logger.error("Wrong encryption key or salt %s" % exc)
        return None
