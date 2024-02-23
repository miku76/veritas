##########################
getting data from nautobot
##########################

*******************
Initialize your sot
*******************

To use veritas first import library and create a sot object.

.. code-block:: python

    from veritas.sot import sot as sot
    my_sot = sot.sot(token="your_token", url="http://ip_or_name:port", ssl_verify=False)

********
Examples
********

.. _sot examples:

get ID and Hostname of a device
-------------------------------
.. code-block:: python

    devices = my_sot.select('id, hostname') \
                    .using('nb.devices') \
                    .where('name=lab.local')

get all hosts that includes 'local'
-----------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('name__ic=local')

get id and hostname of a list of hosts
--------------------------------------
.. code-block:: python

    devices = my_sot.select('id, hostname') \
                    .using('nb.devices') \
                    .where('name=["lab.local","switch.local"]')

get all hosts of a location
---------------------------
.. code-block:: python

    devices = my_sot.select(['hostname']) \
                    .using('nb.devices') \
                    .where('location=default-site')

get all hosts of two locations
------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('location=default-site or location=site_1')

get all hosts with a specific role
----------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('role=network')

get all hosts of platform ios and offline
-----------------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('platform=ios or platform=offline')

get all hosts and primary_ip
----------------------------
.. code-block:: python

    devices = my_sot.select('hostname', 'primary_ip4') \
                    .using('nb.devices') \
                    .where()

get hosts with cf_net=testnet and platform=offline
--------------------------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('cf_net=testnet and platform=offline')

get hosts using multiple (different) cf_fields (or)
---------------------------------------------------
.. code-block:: python

    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('cf_net=testnet or cf_select=zwei')

get hostname and custom_field_data 
----------------------------------
.. code-block:: python

    devices = my_sot.select('hostname, custom_field_data') \
                    .using('nb.devices') \
                    .where('name=lab.local')

get all prefixes within a specififc range
-----------------------------------------
.. code-block:: python

    prefixes = my_sot.select(['prefix','description','vlan', 'location']) \
                    .using('nb.prefixes') \
                    .where('within_include=192.168.0.0/16')

get all prefixes with description, vlan and location
----------------------------------------------------
.. code-block:: python

    all_prefixe = my_sot.select(['prefix','description','vlan', 'location']) \
                        .using('nb.prefixes') \
                        .where()

get id, hostname, and primary_ip of the host with IP=192.168.0.1
-------------------------------------------------------------------
.. code-block:: python

    devices = my_sot.select('id, hostname, primary_ip4') \
                    .using('nb.ipaddresses') \
                    .where('address=192.168.0.1')

get all hosts where the IP address is of type host
--------------------------------------------------
.. code-block:: python

    devices = my_sot.select('id, hostname, primary_ip4') \
                    .using('nb.ipaddresses') \
                    .where('type__ic=host')

get all hosts that have an ip address in a specific prefix range
----------------------------------------------------------------
You can use a transformation to get the device data from the ip address table.

.. code-block:: python

    devices = sot.select('hostname, address, parent, primary_ip4_for, primary_ip4') \
                .using('nb.ipaddresses') \
                .transform('ipaddress_to_device') \
                .where('prefix=192.168.0.0/24')

get all vlans
-------------
.. code-block:: python

    all_vlans = my_sot.select('vid, name, location') \
                    .using('nb.vlans') \
                    .where()

get all vlans of a specific location
------------------------------------
.. code-block:: python

    loc_vlans = my_sot.select('vid, location') \
                    .using('nb.vlans') \
                    .where('location=default-site')

get all locations of our sot
----------------------------
.. code-block:: python

    all_locations = my_sot.select('locations') \
                        .using('nb.general') \
                        .where()

get all tags of our sot
-----------------------
.. code-block:: python
    
    all_tags = my_sot.select('tags') \
                    .using('nb.general') \
                    .where()

get dhcp tag 
------------
.. code-block:: python

    tag = my_sot.select('tags') \
                .using('nb.general') \
                .where('name=dhcp')

get hldm of device
------------------
.. code-block:: python

    hldm = my_sot.get.hldm(device="lab.local")

***********
Join tables
***********

You can join two "tables" using the following syntax:

.. code-block:: python

    vlans = my_sot.select('vlans.vid, vlans.name, vlans.interfaces_as_tagged, devices.name, devices.platform') \
            .using('nb.vlans as vlans') \
            .join('nb.devices as devices') \
            .on('vlans.interfaces_as_tagged[0].device.id = devices.id') \
            .transform(['remove_id', 'to_pandas']) \
            .where('vlans.vid=100')

**************
Transform data
**************

You can transform the data using the following syntax:

.. code-block:: python

    all_devices = my_sot.select('id, hostname, platform.name') \
                        .using('nb.devices') \
                        .transform(['remove_id', 'to_pandas']) \
                        .where()

The following transformations are available:

.. list-table:: available transformations
    :widths: 40 40
    :header-rows: 1

    * - Name
      - Description
    * - remove_id
      - Remove the id from the result
    * - to_pandas
      - Transform the result to a pandas dataframe
    * - values_only
      - Only return the selected values of the result
    * - ipaddress_to_device
      - Returns the device data when the ip address table was used