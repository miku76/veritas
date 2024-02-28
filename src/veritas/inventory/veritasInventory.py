from loguru import logger
from typing import Any, Dict, Type
from nornir.core.inventory import (
    Inventory,
    Group,
    Groups,
    Host,
    Hosts,
    Defaults,
    ConnectionOptions,
    HostOrGroup,
    ParentGroups,
)

# veritas 
from veritas.sot import sot as veritas_sot


def _get_connection_options(data: Dict[str, Any]) -> Dict[str, ConnectionOptions]:
    """return ConnectionOptions object containung all parameter that are needed to connect to a device

    Parameters
    ----------
    data : Dict[str, Any]
        the data to add

    Returns
    -------
    Dict[str, ConnectionOptions]
        the ConnectionOptions options
    """    
    cp = {}
    for cn, c in data.items():
        cp[cn] = ConnectionOptions(
            hostname=c.get("hostname"),
            port=c.get("port"),
            username=c.get("username"),
            password=c.get("password"),
            platform=c.get("platform"),
            extras=c.get("extras"),
        )
    return cp

def _get_defaults(data: Dict[str, Any]) -> Defaults:
    """return Defaults object depending on the data

    Parameters
    ----------
    data : Dict[str, Any]
        the data to add to the object

    Returns
    -------
    Defaults
        Defaults object
    """    
    return Defaults(
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )

def _get_inventory_element(
        type_: Type[HostOrGroup], 
        data: Dict[str, Any], 
        name: str, 
        defaults: Defaults) -> HostOrGroup:
    """return either a Host or a Group object that contains the data

    Parameters
    ----------
    type_ : Type[HostOrGroup]
        The type of the object to return
    data : Dict[str, Any]
        the data to add to the object
    name : str
        the name of the object
    defaults : Defaults
        the default values of the object

    Returns
    -------
    HostOrGroup
        Either a Host or a Group
    """        
    return type_(
        name=name,
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        groups=data.get("groups"),
        defaults=defaults,
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )


class VeritasInventory:
    """VeritasInventory is a class to create a nornir inventory from a veritas SOT

    Parameters
    ----------
    sot : veritas_sot
        The veritas sot object
    where : str
        The where clause to filter the devices
    use_primary_ip : bool
        Use the primary IP address as the hostname
    username : str
        The default username
    password : str
        The default password
    connection_options : Dict[str, Any]
        The default connection options
    data : Dict[str, Any]
        The default data
    select : list
        Additional select values
    host_groups : list
        Additional host groups
    defaults : Dict[str, Any]
        The default values
    groups : Dict[str, Any]
        The groups

    Improtant Note:

    group must be the following format:
    
        groups = {'net': {'data': {'key': 'value'} }}

    Otherwise the data is not automatically added to the host.
    You can get the group data by using the following code:

        nr.inventory.groups['net'].items()

    The group data is added to the host. To get a list of all items of the host use:

        nr.inventory.hosts['lab.local'].items()


    """    
    def __init__(
            self,
            sot: veritas_sot,
            where: str,
            use_primary_ip: bool = True,
            username: str = "",
            password: str = "",
            connection_options: Dict[str, Any] = {},
            data: Dict[str, Any] = {},
            select: list = [],
            host_groups: list = [],
            defaults: Dict[str, Any] = {},
            groups: Dict[str, Any] = {},
            ) -> None:
        self.sot = sot
        self.where = where
        self.use_primary_ip = use_primary_ip
        self.username = username
        self.password = password
        self.connection_options = connection_options
        self.data = data
        self.select = select
        self.host_groups = host_groups
        self.defaults = defaults
        self.groups = groups

        #
        # group must be the following format:
        # groups = {'net': {'data': {'key': 'value'} }}
        #

    def load(self) -> Inventory:
        """load inventory

        Execute a query to get all devices and data from the SOT and create a nornir inventory

        Returns
        -------
        Inventory
            The Inventoty object containing the hosts, the groups and the default values
        """
        hosts = Hosts()
        groups = Groups()

        # the additional select values must be a list
        if isinstance(self.select,str):
            self.select = [self.select]
        # if the user wants 'data' or groups we have to add those fields to our select list
        select = ['hostname', 'primary_ip4', 'platform'] + self.select
        logger.bind(extra="inventory").debug(f'select: {select}')
        sot_devicelist = self.sot.select(select) \
                                 .using('nb.devices') \
                                 .where(self.where)

        # get defaults
        if self.defaults:
            defaults = _get_defaults(self.defaults)
        else:
            defaults = Defaults()

        for device in sot_devicelist:
            hostname = device.get('hostname')
            if not device.get('primary_ip4'):
                logger.error(f'host {hostname} has no primary IPv4 address... skipping')
                continue
            sot_ip4 = device.get('primary_ip4', {}).get('address')
            primary_ip4 = sot_ip4.split('/')[0] if sot_ip4 is not None else hostname
            host_or_ip = primary_ip4 if self.use_primary_ip else hostname
            platform = device.get('platform',{}).get('name','ios') if device['platform'] else 'ios'
            manufacturer = device.get('platform',{}).get('manufacturer',{}).get('name') \
                if device['platform']['manufacturer'] else 'cisco'

            # data is added to the host and can be used by the user
            _data = {'platform': platform,
                     'primary_ip': primary_ip4,
                     'manufacturer': manufacturer}

            for key in self.select:
                if key.startswith('cf_'):
                    ky = key.replace('cf_','')
                    _data[ky] = device.get('custom_field_data',{}).get(ky)
                else:
                    _data[key] = device.get(key)

            # add all keys to data
            for key in self.data.keys():
                _data[key] = self.data.get(key)

            _host_groups = []
            for key in self.host_groups:
                if key.startswith('cf_'):
                    ky = key.replace('cf_','')
                    group = device.get('custom_field_data',{}).get(ky)
                    _host_groups.append(group.replace(' ',''))
                else:
                    group = device.get(key)
                    _host_groups.append(group.replace(' ',''))
            logger.bind(extra="inventory").debug(f'host groups: {" ".join(_host_groups)}')

            device_properties = {'host': hostname,
                                 'hostname': host_or_ip,
                                 'port': 22,
                                 'username': self.username,
                                 'password': self.password,
                                 'platform': platform,
                                 'data': _data,
                                 'groups': _host_groups,
                                 'connection_options': self.connection_options
                                }
            logger.bind(extra="inventory").debug(f'adding device {hostname} to inventory')
            host = _get_inventory_element(Host, device_properties, hostname, defaults)
            hosts[hostname] = host

        for name, group_data in self.groups.items():
            logger.bind(extra="inventory").debug(f'adding group: {name} {group_data}')
            groups[name] = _get_inventory_element(Group, group_data, name, defaults)

        for group in groups.values():
            logger.bind(extra="inventory").debug(f'preparing group: {group}')
            group.groups = ParentGroups([groups[g] for g in group.groups])

        # set the groups for the hosts
        for host in hosts.values():
            host.groups = ParentGroups([groups[g] for g in host.groups])

        logger.bind(extra="nornir").trace(f"inventory: {hosts}")
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
