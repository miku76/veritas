import sys
from loguru import logger
from importlib.metadata import version
import functools
import inspect
from functools import partialmethod
from datetime import time

# veritas
from veritas.messagebus import rabbitmq as mb_rabbitmq
from veritas.messagebus import zeromq as mb_zermomq
from veritas.messagebus import database as mb_database


__version__ = version("veritas")

def create_logger_environment(config, cfg_loglevel=None, cfg_loghandler=None, app=None, uuid=None):
    """return database, rabbitmq and formatter"""

    # we are using our 'custom' journal loglevel. But this only works when using 
    # loguru without zeromq
    journal_loglevel = 60

    loglevel = cfg_loglevel.upper() if cfg_loglevel \
        else config.get('general',{}).get('logging',{}).get('loglevel', 'INFO')
    handler_txt = cfg_loghandler if cfg_loghandler \
        else config.get('general',{}).get('logging',{}).get('handler', 'sys.stdout')
    
    # loguru uses UPPER case loglevels
    loglevel = loglevel.upper()

    # evaluate handler
    if handler_txt == 'sys.stdout' or handler_txt == 'stdout':
        loghandler = sys.stdout
    elif handler_txt == 'sys.stderr' or handler_txt == 'stderr':
        loghandler = sys.stderr
    else:
        loghandler = handler_txt

    # if uuid is set we have to check to which bus we have to send the message
    log_uuid_to = config.get('general',{}).get('logging',{})\
                        .get('log_uuid_to') if uuid else None

    # do we have to enable our database output
    if log_uuid_to == "database" or config.get('general',{}).get('logging',{}).get('log_to_database', False):
        database = config.get('general',{}).get('logging',{}).get('database')
    else:
        database = None

    # check if we have to enable the rabbitmq mechanism
    if log_uuid_to == "rabbitmq" or config.get('general',{}).get('logging',{}).get('log_to_rabbitmq', False):
        rabbitmq = config.get('general',{}).get('logging',{}).get('rabbitmq')
    else:
        rabbitmq = None

    # if check if we have to enable the zeromq mechanism
    if log_uuid_to == "zeromq" or config.get('general',{}).get('logging',{}).get('log_to_zeromq', False):
        zeromq = config.get('general',{}).get('logging',{}).get('zeromq')
        # zeromq does not support custom loglevels!
        journal_loglevel = 40
    else:
        zeromq = None

    # configure formatter
    if loglevel == "TRACE":
        logger_format = (
                "<green>{time:HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name: <18.18}</cyan> | <cyan>{function: <15.15}</cyan> | <cyan>{line: >3}</cyan> | "
                "{extra[extra]: <12} | <level>{message}</level>"
        )
    elif loglevel == "DEBUG":
        logger_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name: <18.18}</cyan> | <cyan>{function: <15.15}</cyan> | <cyan>{line: >3}</cyan> | "
                "{extra[extra]: <12} | <level>{message}</level>"
        )
    else:
        logger_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "{extra[extra]: <12} | <level>{message}</level>"
        )

    # remove existing logger
    logger.remove()
    logger.configure(extra={"extra": "unset"})
    logger.add(loghandler, level=loglevel, format=logger_format)

    # create JOURNAL loglevel (does not work if zeromq)
    method_list = [method for method in dir(logger) if method.startswith('__') is False]
    if 'journal' not in method_list:
        logger.level("journal", no=journal_loglevel, color="<yellow>")
        logger.__class__.journal = partialmethod(logger.__class__.log, "journal")

    if rabbitmq:
        logger.debug(f'enabling rabbitmq messagebus loglevel: {loglevel}')
        logger.add(mb_rabbitmq.Rabbitmq(
                   app=app,
                   uuid=uuid,
                   rabbitmq=rabbitmq),
            level=loglevel,
            serialize=True)
    
    if database:
        logger.debug(f'enabling database messagebus loglevel: {loglevel}')
        logger.add(mb_database.Zeromq(
                   app=app,
                   uuid=uuid, 
                   database=database),
            level=loglevel,
            serialize=True)

    if zeromq:
        logger.debug(f'enabling zeromq messagebus loglevel: {loglevel}')
        logger.add(mb_zermomq.Database(
                   app=app,
                   uuid=uuid, 
                   zeromq=zeromq),
            level=loglevel,
            serialize=True)

def minimal_logger(loglevel):
    loghandler = sys.stdout
    # configure formatter
    if loglevel.upper() == "DEBUG":
        logger_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name: <18.18}</cyan> | <cyan>{function: <15.15}</cyan> | <cyan>{line: >3}</cyan> | "
                "{extra[extra]: <12} | <level>{message}</level>"
        )
    else:
        logger_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "{extra[extra]: <12} | <level>{message}</level>"
        )

    # remove existing logger
    logger.remove()
    logger.configure(extra={"extra": "unset"})
    logger.add(loghandler, level=loglevel.upper(), format=logger_format)

def debug_parameter(*, entry=True, exit=True, level="DEBUG"):

    def wrapper(func):
        name = func.__name__

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            logger_ = logger.opt(depth=1)
            if entry:
                logger_.log(level, "Entering '{}' (args={}, kwargs={})", name, args, kwargs)
            result = func(*args, **kwargs)
            if exit:
                logger_.log(level, "Exiting '{}' (result={})", name, result)
            return result
        return wrapped
    return wrapper

def timeit(func):

    def wrapped(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.debug("Function '{}' executed in {:f} s", func.__name__, end - start)
        return result

    return wrapped
