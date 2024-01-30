*********
Migration
*********

veritas und das dazugehörige toolkit wuerden entwickelt, um ein kommerzielles Netzwerkmanagement-System 
durch eine open-source Lösung abzulösen. Das bisher eingesetzte System bestand nicht nur aus einer Datenbank, 
in der alle Netzwerlgeräte gespeichert wurden. Bestandteil waren auch verschiedene Module, um Netzwerkgeräte 
zu überwachen, Daten per SNMP abzuholen, Konfigurationen zu sichern und IP-Adressen zu verwalten. 

Bei einer Migration ist es besonders wichtig, den Datenbestand möglichst exakt in das neue System zu übernehmen. 
Da die verschiedenen Systeme alle sehr unterschiedlich sind, können die Daten leider nicht 1:1 übernommen werden.
Um eine Migration erfolgreich durchzuführen, müssen im Altsystem die Daten exportiert, anschließend angepasst und 
in das neue System imporiert werden.

Um diesen Prozess weitestgehend automatisiert durchzuführen, wurde veritas entwickelt. 

Der Export von Daten aus dem Altsystem kann nur mit Tools erfolgen, die entweder Teil des Altsystems sind oder 
die das vorhandene Datenformat (die gleiche Datenbank usw.) unterstützen.

Der Exportvorgang kann von Veritas nicht unterstützt werden. Allerdings kann Veritas so angepasst werden, dass es 
die exportierten Daten lesen und in nautobot importieren kann.

.. toctree::
   :maxdepth: 2


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`