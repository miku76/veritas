****************
Quickstart Guide
****************

This is a quick (and hopefully not dirty) quickstart guide to install veritas.

Installing veritas
==================

The easiest way is to use a virtual python-environment. There are different ways to create such an environment. conda offers one possibility. If you have conda installed, you can create a new environment as follows:

.. code-block:: python

    conda create --name veritas python=3.11


to activate the environment:

.. code-block:: python

    conda activate veritas


To install veritas, poetry must first be installed.

.. code-block:: python

    conda install poetry


to install veritas:

.. code-block:: python

    >>> git clone https://github.com/veritas-sot/veritas.git
    ...
    >>> cd veritas
    >>> poetry install


This will resolve all dependencies and install the library.

Guide
=====

.. toctree::
   :maxdepth: 2

   api
