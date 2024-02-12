
from loguru import logger

# veritas
from veritas.onboarding import plugins

@plugins.vlan_properties('ios')
def get_vlan_properties(ciscoconf, device_defaults):
    global_vlans, svi, trunk_vlans = ciscoconf.get_vlans()
    list_of_vlans = []
    all_vlans = {}
    location = device_defaults['location']

    for vlan in global_vlans:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': location})

    for vlan in svi:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': device_defaults['location']})

    for vlan in trunk_vlans:
        vid = vlan.get('vid')
        name = vlan.get('name','')
        if '-' in vid or ',' in vid:
            continue
        if f'{vid}__{location}' not in all_vlans:
            all_vlans[f'{vid}__{location}'] = True
            list_of_vlans.append({'name': name,
                                  'vid': vid,
                                  'status': {'name': 'Active'},
                                  'location': device_defaults['location']})

    return list_of_vlans
