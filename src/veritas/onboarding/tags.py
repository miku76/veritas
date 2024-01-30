import re
import yaml
import os
import glob
from loguru import logger


def get_tag_properties(device_fqdn, device_properties, device_facts, configparser, onboarding_config):

    tags = []

    default_tags = from_default(device_properties)
    file_tags = from_file(device_fqdn, device_properties, device_facts, configparser, onboarding_config)

    for tag in default_tags:
        tags.append(tag)
    for tag in file_tags:
        tags.append(tag)

    return tags

def from_default(device_properties):
    logger.debug('adding tags from default values')

    response = []

    if 'tag' in device_properties:
        for tag in device_properties['tag'].split(','):
            response.append(property = {'name': tag, 'scope': 'dcim.device'})

    return response

def from_file(device_fqdn, device_properties, device_facts, configparser, onboarding_config):

    logger.debug('adding tags from files')

    response = []

    basedir = onboarding_config.get('git').get('app_configs').get('path')
    directory = os.path.join(basedir, './onboarding/tags/')

    # we read all *.yaml files in our tags config dir
    for filename in glob.glob(os.path.join(directory, "*.yaml")):
        logger.debug(f'reading {filename.rsplit("/")[-1]}')
        config = read_file(filename, device_properties)
        if config is None:
            continue

        # get the source. It is either a section or a (named) regular expression
        if 'section' in config['source']:
            device_config = configparser.get_section(config['source']['section'])
            response += parse_config(device_config, device_fqdn, config)
        elif 'fullconfig' in config['source']:
            device_config = configparser.get_device_config().splitlines()
            response += parse_config(device_config, device_fqdn, config)
        elif 'device' in config['source']:
            response += parse_device_properties(device_fqdn,
                                                device_facts,
                                                config['source']['device'],
                                                config)
        else:
            logger.error("unknown source %s" % config['source'])

    return response

def read_file(filename, device_properties):
    with open(filename) as f:
        config = {}
        logger.debug(f'opening {filename.rsplit("/")[-1]} to read custom field config')
        try:
            config = yaml.safe_load(f.read())
            if config is None:
                logger.error(f'could not parse {filename}')
                return None
        except Exception as exc:
            logger.error(f'could not read {filename}; got exception {exc}')
            return None

        name = config.get('name')
        platform = config.get('platform')
        if not config.get('active'):
            logger.debug(f'tags {name} in {filename.rsplit("/")[-1]} is not active')
            return None
        if platform is not None:
            device_platform = device_properties.get('platform',{}).get('name','')
            if platform != 'all' and platform != device_platform:
                logger.debug(f'skipping custom field {name} wrong platform {platform}')
                return None
        return config

def parse_device_properties(device_fqdn, device_facts, host_or_ip, config):
    logger.debug('looking for tags depending on hostname or ip')

    list_of_items = []
    list_of_ip = []
    list_of_hostnames = []
    list_of_models = []
    list_of_manufacturers = []
    list_of_os_version = []
    response = []

    if isinstance(host_or_ip, dict):
        list_of_items.append(host_or_ip)
    else:
        list_of_items = host_or_ip

    for item in list_of_items:
        if 'ip' in item:
            list_of_ip.append(item['ip'])
        if 'hostname' in item:
            list_of_hostnames.append(item['hostname'])
        if 'model' in item:
            list_of_models.append(item['model'])
        if 'manufacturer' in item:
            list_of_manufacturers.append(item['manufacturer'])
        if 'os_version' in item:
            list_of_os_version.append(item['os_version'])

    if device_fqdn in list_of_hostnames or device_facts['args.device'] in list_of_ip or \
       device_facts['model'] in list_of_models or device_facts['manufacturer'] in list_of_manufacturers or \
       device_facts['os_version'] in list_of_os_version:
        if 'tags' in config:
            for tag in config['tags']:
                response.append({'name': tag['name'], 'scope': 'dcim.device'})
    return response

def parse_config(device_config, device_fqdn, config):
    response = []
    for tags in config.get('tags',[]):
        pattern = tags.get('pattern', None)
        contains = tags.get('contains', None)
        scope_of_tag = tags.get('scope', 'dcim.device')
        name_of_tag = tags.get('name')
        if pattern:
            logger.debug(f'name: {name_of_tag} scope: {scope_of_tag} pattern: {pattern}')
            compiled = re.compile(pattern)
        elif contains:
            logger.debug(f'name: {name_of_tag} scope: {scope_of_tag} string: {contains}')
        interface = None
        for line in device_config:
            # check if we have an interface that is needed with scope dcim.interface
            if line.lower().startswith('interface '):
                interface = line[10:]
            if pattern:
                match = compiled.match(line)
                if match:
                    logger.debug(f'pattern found on interface {interface}')
                    if scope_of_tag == "dcim.interface" and interface is not None:
                       response.append({'name': name_of_tag,
                                        'interface': interface,
                                        'scope': scope_of_tag})
                    elif scope_of_tag == "dcim.device":
                        response.append({'name': name_of_tag,
                                     'scope': scope_of_tag})
            elif contains and contains in line:
                logger.debug(f'string found on interface {interface}')
                if scope_of_tag == "dcim.interface" and interface is not None:
                    response.append({'name': name_of_tag,
                                     'interface': interface,
                                     'scope': scope_of_tag})
                elif scope_of_tag == "dcim.device":
                    response.append({'name': name_of_tag,
                                     'scope': scope_of_tag})
    return response
