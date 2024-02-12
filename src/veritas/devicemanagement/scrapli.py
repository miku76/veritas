import os
import importlib
import logging
from loguru import logger
from scrapli import Scrapli
from scrapli_cfg import ScrapliCfg
from ntc_templates.parse import parse_output
from ..tools import tools


def get_loglevel(level):
    if level.lower() == 'debug':
        return logging.DEBUG
    elif level.lower() == 'info':
        return logging.INFO
    elif level.lower() == 'critical':
        return logging.CRITICAL
    elif level.lower() == 'error':
        return logging.ERROR
    elif level.lower() == 'none':
        return 100
    else:
        return logging.NOTSET


class Devicemanagement:

    def __init__(self, **kwargs):
        self._connection = None
        self._ip_address = kwargs.get('ip')
        self._platform = kwargs.get('platform', 'ios')
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._port = kwargs.get('port', 22)
        self._manufacturer = kwargs.get('manufacturer', 'cisco')

        if 'scrapli_loglevel' in kwargs:
            logging.getLogger('scrapli').setLevel(get_loglevel(kwargs['scrapli_loglevel']))
            logging.getLogger('scrapli').propagate = True
        else:
            logging.getLogger('scrapli').setLevel(logging.ERROR)
            logging.getLogger('scrapli').propagate = False

    def open(self):

        # we have to map the driver to our srapli driver / platform
        #
        # napalm | scrapli
        # -------|------------
        # ios    | cisco_iosxe
        # iosxr  | cisco_iosxr
        # nxos   | cisco_nxos

        mapping = {'ios': 'cisco_iosxe',
                   'iosxr': 'cisco_iosxr',
                   'nxos': 'cisco_nxos'
                   }
        driver = mapping.get(self._platform)
        if driver is None:
            return False

        device = {
            "host": self._ip_address,
            "auth_username": self._username,
            "auth_password": self._password,
            "auth_strict_key": False,
            "platform": driver,
            "port": self._port,
            "ssh_config_file": True
        }

        # fow later use
        # "auth_private_key": f"{SSH_KEYS_EXAMPLE_DIR}/scrapli_key",

        self._connection = Scrapli(**device)
        logger.debug("opening connection to device (%s)" % self._ip_address)
        try:
            self._connection.open()
            self._scrapli_cfg = ScrapliCfg(conn=self._connection)
        except Exception as exc:
            logger.error(f'could not connect to {self._ip_address} {exc}')
            return False

        return True

    def close(self):
        logger.debug("closing connection to device (%s)" % self._ip_address)
        try:
            self._connection.close()
        except Exception:
            # is it interesting to log something? I guess not
            pass

    def disable_paging(self):
        if not self._connection:
                if not self.open():
                    return None
        response = self._connection.send_command('terminal length 0')
        return response.result

    def get_config(self, configtype='running-config'):
        logger.debug(f'send show {configtype} to {self._ip_address}')
        if not self._connection:
                if not self.open():
                    return None
        response = self._connection.send_command(f'show {configtype}')
        return response.result

    def write_config(self):
        if not self._connection:
                if not self.open():
                    return None
        logger.debug(f'writing config on {self._ip_address}')
        return self._scrapli_cfg.save_config()

    def send_configs_from_file(self, configfile):
        if not self._connection:
                if not self.open():
                    return False
        logger.debug(f'sending config {configfile} to {self._ip_address}')
        return self._connection.send_configs_from_file(configfile)

    def send_commands(self, commands):
        if not self._connection:
            if not self.open():
                return None

        return self._connection.send_commands(commands)

    def send_configs(self, commands):
        if not self._connection:
            if not self.open():
                return None

        return self._connection.send_configs(commands)

    def send(self, *unnamed, **named):

        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        if isinstance(properties, str):
            return self.send_and_parse_command(commands=[properties])
        else:
            return self.send_and_parse_command(*unnamed, **named)

    def send_and_parse_command(self, *unnamed, **named):
        """send command(s) to device and parse output"""

        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        commands = properties.get('commands')
        use_own_templates = properties.get('own_templates', False)

        # init return value
        result = {}

        if use_own_templates:
            package = f'{__name__.split(".")[0]}.devicemanagement.data.textfsm'
            directory = str(importlib.resources.files(package)._paths[0])
            logger.debug(f'looking for ntc_templates in {directory}')
            os.environ["NTC_TEMPLATES_DIR"] = directory

        if not self._connection:
            if not self.open():
                return None

        platform = f'{self._manufacturer}_{self._platform}'

        for cmd in commands:

            try:
                logger.debug(f'sending {cmd}')
                response = self._connection.send_command(cmd)
                data = response.result
            except Exception as exc:
                logger.error(f'could not send command  to device; got exception {exc}')
                return None

            try:
                logger.debug(f'parsing output; platform={platform} command={cmd}')
                result[cmd] = parse_output(platform=platform, command=cmd, data=data)
            except Exception as exc:
                logger.error(f'could not parse output {exc}')
                return None

        return result

    def get_facts(self):
        """get show version and show hosts summary from device"""

        facts = {}

        # get values from device
        # we have to use our own templates because there is a little bug parsing
        # show hosts summary on a iosv device
        values = self.send_and_parse_command(
            commands=['show version', 'show hosts summary'],
            own_templates=True)

        if not values:
            logger.error('got na values')
            return None

        # parse values to get facts
        facts["manufacturer"] = self._manufacturer
        if "show version" in values:
            facts["os_version"] = values["show version"][0].get("version",None)
            if facts["os_version"] is None:
                # nxos uses OS instead of version
                facts["os_version"] = values["show version"][0].get('OS', 'unknown')
            facts["software_image"] = values["show version"][0].get("software_image", None)
            if facts["software_image"] is None:
                # nxos uses BOOT_IMAGE instead of software_image
                facts["software_image"] = values["show version"][0].get("boot_image",'unknown')
            facts["serial_number"] = values["show version"][0]["serial"]
            if 'hardware' in values["show version"][0]:
                facts["model"] = values["show version"][0]["hardware"][0]
            else:
                # nxos uses PLATFORM instead of HARDWARE
                model = values["show version"][0].get('platform',None)
                if model is None:
                    facts["model"] = "default_type"
                else:
                    facts["model"] = "nexus-%s" % model
            facts["hostname"] = values["show version"][0]["hostname"]

        if "show hosts summary" in values and len(values["show hosts summary"]) > 0:
            facts["fqdn"] = "%s.%s" % (facts.get("hostname"), values["show hosts summary"][0]["default_domain"])
        else:
            facts["fqdn"] = facts.get("hostname")

        # hostnames and fqdn are always lower case
        facts['fqdn'] = facts['fqdn'].lower()
        facts['hostname'] = facts['hostname'].lower()

        return facts

    def replace_config(self, config):
        if not self._connection:
            if not self.open():
                return None
        self._connection.prepare()
        self._connection.load_config(config=config, replace=True)
        self._connection.commit_config()
        self._connection.cleanup()

    def prepare(self):
        if not self._connection:
            if not self.open():
                return None        
        self._scrapli_cfg.prepare()

    def load_config(self, config, replace=False):
        """load config to device. If replace=True the config is replaced.
           If replace=False the config is merged"""     
        return self._scrapli_cfg.load_config(config=config, replace=replace)
    
    def abort_config(self):     
        return self._scrapli_cfg.abort_config()

    def commit_config(self):     
        return self._scrapli_cfg.commit_config()

    def diff_config(self):
        """return diff between the running and the specified config
        
        you can use the diff_result to:

        - print(diff_result.device_diff)
        - print(diff_result.unified_diff)
        - print(diff_result.side_by_side_diff)
        
        """
        return self._scrapli_cfg.diff_config()

    def cleanup(self):
        self._scrapli_cfg.cleanup()
