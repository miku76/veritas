from loguru import logger
from ntc_templates.parse import parse_output
import napalm
import importlib
import os
from importlib import resources
from ..tools import tools

class Devicemanagement:

    def __init__(self, **kwargs):
        self._connection = None
        self._ip_address = kwargs.get('ip')
        self._platform = kwargs.get('platform', 'ios')
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._port = kwargs.get('port', 22)
        self._manufacturer = kwargs.get('manufacturer', 'cisco')
        self._timeout = kwargs.get('timeout', 60)

    def open(self, optional_args={}):
        # Use the appropriate network driver to connect to the device:
        driver = napalm.get_network_driver(self._platform)

        opt ={"port": self._port}
        opt.update(optional_args)

        self._connection = driver(
            hostname=self._ip_address,
            username=self._username,
            password=self._password,
            optional_args=opt
        )

        logger.debug(f'opening connection to {self._ip_address}')
        try:
            self._connection.open()
            logger.debug(f'connection established')
        except (SSHException, ConnectionException) as e:
            logger.error(f'Failed to connect to {self._ip_address} due to {type(e).__name__}')
    
    def has_open_connection(self):
        if self._connection:
            return True
        else:
            return False
    
    def get_connection(self):
        return self._connection

    def close(self):
        logger.debug("closing connection to device (%s)" % self._ip_address)
        self._connection.close()
    
    def disable_paging(self):
        if not self._connection:
                if not self.open():
                    return None
        response = self._connection.cli(f'terminal length 0')
        return response.result

    def get_config(self, configtype='running'):
        logger.debug(f'send show {configtype} to {self._ip_address}')
        if not self._connection:
                if not self.open():
                    return None
        config = self._connection.get_config(retrieve=configtype)
        return config.get(configtype)

    def write_config(self):
        if not self._connection:
                if not self.open():
                    return None
        logger.debug(f'writing config on {self._ip_address}')
        return self._connection._netmiko_device.save_config()

    def send_configs_from_file(self, configfile):
        if not self._connection:
                if not self.open():
                    return False

        with open(configfile, 'r') as cf:
            commands = [line.rstrip() for line in cf]

        logger.debug(f'sending config {configfile} to {self._ip_address}')
        return self._connection.cli(commands)

    def send_commands(self, commands):
        if not self._connection:
            if not self.open():
                return None

        return self._connection.cli(commands)

    def send_configs(self, commands):
        if not self._connection:
            if not self.open():
                return None

        return self._connection.cli(commands)

    def send(self, *unnamed, **named):
        if not self._connection:
            if not self.open():
                return None

        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        if isinstance(properties, str):
            return self.send_and_parse_command(commands=[properties])
        else:
            return self.send_and_parse_command(*unnamed, **named)

    def send_and_parse_command(self, *unnamed, **named):
        """send command(s) to device and parse output"""
        if not self._connection:
            if not self.open():
                return None

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

        platform = f'{self._manufacturer}_{self._platform}'

        data = self._connection.cli(commands)

        for cmd in commands:
            try:
                logger.debug(f'parsing output; platform={platform} command={cmd}')
                result[cmd] = parse_output(platform=platform, command=cmd, data=data[cmd])
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
        values = self.send_and_parse_command(commands=['show version', 'show hosts summary'],
                                             own_templates=True)

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

    def replace_config(self, filename):
        if not self._connection:
            if not self.open():
                return None
        logger.debug(f'replace configuration with {filename}')
        return self._connection.load_replace_candidate(filename=filename)

    def load_config(self, config):
        if not self._connection:
            if not self.open():
                return None
        return self._connection.load_merge_candidate(config=config)

    def merge_config(self, config):
        if not self._connection:
            if not self.open():
                return None
        return self._connection.load_merge_candidate(config=config)

    def abort_config(self, config=None):
        if not self._connection:
            if not self.open():
                return None
        logger.debug(f'discarding config')
        return self._connection.discard_config()

    def commit_config(self, config=None, revert_in=None):
        if not self._connection:
            if not self.open():
                return None
        if revert_in:
            logger.debug(f'commit config revert_in={revert_in}')
            return self._connection.commit_config(revert_in=revert_in)
        else:
            logger.debug(f'commit config')
            return self._connection.commit_config()

    def diff_config(self, config=None):
        if not self._connection:
            if not self.open():
                return None
        return self._connection.compare_config()

    def has_pending_commits(self):
        if not self._connection:
            if not self.open():
                return None
        return self._connection.has_pending_commit()

    def rollback(self):
        if not self._connection:
            if not self.open():
                return None
        logger.debug(f'rollback config')
        return self._connection.rollback()
    
