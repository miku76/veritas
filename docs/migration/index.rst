*********
Migration
*********

veritas and the associated toolkit were developed to replace a commercial network management 
system with an open-source solution. The system used so far did not just consist of a database 
in which all network devices were stored. It also included various modules for monitoring network devices, 
fetching data via SNMP, backing up configurations and managing IP addresses.

During a migration, it is particularly important to transfer the data as precisely as possible into the new system.
Since the various systems are all very different, the data unfortunately cannot be transferred 1:1.
In order to successfully migrate a system, the data in the old system must be exported, then adapted and
be imported into the new system.

Veritas was developed to support this process as automated as possible.

Export data
===========

Exporting data from the legacy system can only be achieved using tools that are either part of the legacy 
system or support the data format (the same database, etc.).

Veritas cannot support the export process. However, Veritas can be customized to read the exported data and 
import it into nautobot.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`