**********
Onboarding
**********

Examples how to onboard a device...

.. code-block:: python

    from veritas.sot import sot as veritas_sot

    device_properties = {
        'name': "lab.local",
        'location': {'name': "my_location"},
        'status': {'name': 'Active'},
        'serial': 'unknown',
        'role': {'name': 'network'},
        'device_type': {'model': "my_device_type"},
        'platform': {'name': "my_platform"},
        'custom_fields': {'tag': 'value'},
        'tags': ["tags"]
    }

    interface_properties = [
        {'name': "Mgmt0",
        'ip_addresses': [{'address': "192.168.0.1/24",
                        'status': {'name': 'Active'}
                        }],
        'description': 'Primary Interface',
        'type': '1000base-t',
        'status': {'name': 'Active'} 
        }
    ]

    vlan_properties = {}
    primary_interface = "Mgmt0"

    sot = veritas_sot.Sot(token=token, url=url, ssl_verify=ssl_verify)

    new_device = sot.onboarding \
                    .interfaces(interface_properties) \
                    .vlans(vlan_properties) \
                    .primary_interface(primary_interface) \
                    .add_prefix(False) \
                    .add_device(device_properties)
