from dataclasses import dataclass, field, fields, is_dataclass, asdict


# decorator to wrap original __init__ 
def nested_dataclass(*args, **kwargs): 
    def wrapper(check_class): 
        # passing class to investigate 
        check_class = dataclass(check_class, **kwargs) 
        o_init = check_class.__init__ 

        def __init__(self, *args, **kwargs): 
            for name, value in kwargs.items():
                # getting field type
                ft = check_class.__annotations__.get(name, None)
                if is_dataclass(ft) and isinstance(value, dict): 
                    obj = ft(**value) 
                    kwargs[name]= obj 
                o_init(self, *args, **kwargs)
            self.check_type()
        check_class.__init__=__init__
        return check_class 
    return wrapper(args[0]) if args else wrapper 

@dataclass
class StatusData():
    name: str = "Active"

    def __getitem__(self, property_name):
        return self.__dict__[property_name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

@dataclass
class RoleData():
    name: str = "network"

    def __getitem__(self, property_name):
        return self.__dict__[property_name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

@dataclass
class TenantData():
    name: str
    group : str = None
    description: str = None
    tags: list[list] = field(default_factory=list)

    def __getitem__(self, property_name):
        keys = property_name.split('.')
        remaining = '.'.join(keys[1:])
        if len(keys) > 1 and keys[0] == 'tags':
            return self.tags.__getitem__(remaining)
        else:
            return self.__dict__[property_name]

    def __setitem__(self, name, value):
        keys = name.split('.')
        remaining = '.'.join(keys[1:])
        if keys[0] == 'tags':
            self.tags.__setitem__(remaining, value)
        else:
            self.__dict__[name] = value

@dataclass
class LocationData():
    name : str
    location_type: str
    parent: str = None
    status: str = "Active"

    def __getitem__(self, property_name):
        return self.__dict__[property_name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

@dataclass
class RackData():
    position: int = None
    group: str = None
    rack: str = None
    face: str = None

    def __getitem__(self, property_name):
        return self.__dict__[property_name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

@dataclass
class IPaddressData():
    address: str
    status: StatusData = None

    def __getitem__(self, property_name):
        keys = property_name.split('.')
        remaining = '.'.join(keys[1:])
        if len(keys) > 1 and keys[0] == 'status':
            return self.status.__getitem__(remaining)
        else:
            return self.__dict__[property_name]

    def __setitem__(self, name, value):
        keys = name.split('.')
        remaining = '.'.join(keys[1:])
        if keys[0] == 'status':
            self.status.__setitem__(remaining, value)
        else:
            self.__dict__[name] = value

    def __post_init__(self):
        if not self.status:
            self.status = StatusData()
        elif isinstance(self.status, str):
            self.status = StatusData(name=self.status)
        elif isinstance(self.status, dict):
            self.status = StatusData(**self.status)
        elif not isinstance(self.status, StatusData):
            raise ValueError('status must be of type StatusData')

@dataclass
class InterfaceData():
    name: str
    type: str
    enabled: bool = True
    description: str = None
    ip_addresses: list[IPaddressData] = field(default_factory=list)
    mode: str = None
    untagged_vlan: list[dict] = field(default_factory=dict)
    tagged_vlans: list[dict] = field(default_factory=dict)

    def __getitem__(self, property_name):
        return self.__dict__[property_name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value
    
    def __post_init__(self):
        if not self.ip_addresses:
            self.ip_addresses = []
        elif isinstance(self.ip_addresses, list):
            ip_list = []
            for item in self.ip_addresses:
                if isinstance(item, dict):
                    ip = IPaddressData(**item)
                    ip_list.append(ip)
                elif not isinstance(item, IPaddressData):
                    raise ValueError('ip_addresses must be of type IPaddressData')
            self.ip_addresses = ip_list
        elif not isinstance(self.ip_addresses, list):
            raise ValueError('ip_addresses must be of type list')

        if not self.untagged_vlan:
            self.untagged_vlan = []
        elif isinstance(self.untagged_vlan, list):
            vlan_list = []
            for item in self.untagged_vlan:
                if isinstance(item, dict):
                    vlan_list.append(item)
                else:
                    raise ValueError('untagged_vlan must be of type dict')
            self.untagged_vlan = vlan_list
        elif not isinstance(self.untagged_vlan, list):
            raise ValueError('untagged_vlan must be of type list')

        if not self.tagged_vlans:
            self.tagged_vlans = []
        elif isinstance(self.tagged_vlans, list):
            vlan_list = []
            for item in self.tagged_vlans:
                if isinstance(item, dict):
                    vlan_list.append(item)
                else:
                    raise ValueError('tagged_vlans must be of type dict')
            self.tagged_vlans = vlan_list
        elif not isinstance(self.tagged_vlans, list):
            raise ValueError('tagged_vlans must be of type list')

@dataclass
class DeviceData():
    # name, role, devive_type, status and location are mandatory
    name: str
    role: RoleData
    device_type: str
    location: LocationData

    # list of interfaces
    interfaces: list[InterfaceData] = field(default_factory=list)

    status: StatusData = None
    rack: RackData = None
    serial: str = ''
    manufacturer: str = None
    asset_tag: str = None
    platform: str = None
    primary_ipv4: str = None
    primary_ipv6: str = None
    device_redudancy_group: str = None
    device_redudancy_priority: int = None

    tenant: str = None
    # Remeinaing fields
    tags: list[int] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict):
        return cls(**payload)

    def check_type(self):
        for name, field_type in self.__annotations__.items():
            if name in self.__dict__:
                provided_key = self.__dict__[name]
            else:
                continue

            # we ignore fields that are not provided (are None)
            if not provided_key:
                continue

            try:
                type_matches = isinstance(provided_key, field_type)
            except TypeError:
                type_matches = isinstance(provided_key, field_type.__args__)

            if not type_matches:
                raise TypeError(
                    f"The field '{name}' is of type '{type(provided_key)}', but "
                    f"should be of type '{field_type}' instead."
                )

    def __getitem__(self, property_name):
        keys = property_name.split('.')
        remaining = '.'.join(keys[1:])
        if len(keys) > 1 and keys[0] == 'location':
            return self.location.__getitem__(remaining)
        elif len(keys) > 1 and keys[0] == 'rack':
            return self.rack.__getitem__(remaining)
        else:
            return self.__dict__[property_name]

    def __setitem__(self, name, value):
        keys = name.split('.')
        remaining = '.'.join(keys[1:])
        if keys[0] == 'location':
            if not self.location:
                self.location = LocationData()
            self.location.__setitem__(remaining, value)
        elif keys[0] == 'rack':
            if not self.rack:
                self.rack = RackData()
            self.rack.__setitem__(remaining, value)
        elif keys[0] == 'status':
            if not self.status:
                self.status = StatusData()
            self.status.__setitem__(remaining, value)
        else:
            if name not in self.__annotations__:
                raise AttributeError (f"Attribute {name} not found in DeviceData")

    # public methods

    def clean(self):
        props = asdict(self)
        self.remove_empty_values(props)
        return props

    def remove_empty_values(self, dictionary:dict):
        # run recusively through dictionary and remove empty values
        for key, value in list(dictionary.items()):
            if isinstance(value, dict):
                self.remove_empty_values(value)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self.remove_empty_values(item)
            if value in [None, '', [], {}]:
                del dictionary[key]
