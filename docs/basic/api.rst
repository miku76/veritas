Creating a veritas Instance
===========================
To start, instantiate an :py:class:`~veritas.sot.sot` object

.. code-block:: python

    from veritas.sot import sot as veritas_sot
    my_sot = veritas_sot.sot(token="your_token", 
                             url="http://ip_or_name:port", 
                             ssl_verify=False,
                             debug=False)

Use this object to query nautobot. 


Query nautobot
==============

.. code-block:: python

    # get hostnames of ALL devices that contains 'local' in its name
    devices = my_sot.select('hostname') \
                    .using('nb.devices') \
                    .where('name__ic=local')

You can find numerous examples of how this can be done :ref:`here <sot examples>`.


Reading a YAML config file
==========================
To read your script based config use ``veritas.tools.get_miniapp_config``

.. note::

    veritas looks in the following directories...

    Priority (in this order):
        1. user specified file (if absolute path)
        2. config in home directory ~/.veritas
        3. config in local directory
        4. config in local ./conf/ directory
        5. config in /etc/veritas/

.. code-block:: python

    from veritas.tools import tools
    local_config_file = tools.get_miniapp_config('script_bakery', BASEDIR, args.config)

Create your Logging environment
===============================
.. code-block:: python

    import veritas.logging
    veritas.logging.create_logger_environment(
        config=local_config_file, 
        cfg_loglevel=args.loglevel,
        cfg_loghandler=args.loghandler,
        app='your_script_name',
        uuid=uuid)

.. note::

    veritas uses loguru to log messages. You can use loguru by

    .. code-block:: python

        >>> from loguru import logger
    
    If you want your data to be logged into a database use the :py:class:`~veritas.messagebus`
    to enable rabbitmq and use a dispatcher to collect the logs and add them to your database. 
    Have a look into the toolkit's config how to enable the messagebus and how to use the dispatcher 
    that comes with the toolkit.

Read Username and Password from Profile
=======================================
Profiles are used to login to your network devices. Because veritas is supposed to log in to devices 
fully automatically, these logins must be stored securely. veritas uses a profile config file to 
achieve this. To ensure that the password cannot be read from a file as plain text, the password is 
saved in encrypted form.

.. tip::

    To be completely sure that no one gets access to the login data, another mechanism should be used in 
    a production environment. Such a mechanism could be a vault, for example. An implementation of such a 
    mechanism is (currently) not part of veritas.

.. code-block:: python

    import os
    from veritas.tools import tools

    # Get the path to the directory this file is in
    BASEDIR = os.path.abspath(os.path.dirname(__file__))

    # load profiles
    profile_config = tools.get_miniapp_config('your_appname', BASEDIR, 'profiles.yaml')

    # get username and password either from profile
    username, password = tools.get_username_and_password(
        sot,
        profile_config,
        args.profile,
        args.username,
        args.password)

Use nornir
==========
nornir can be used to configure hundreds of devices as quickly and easily as possible.

.. code-block:: python

    from nornir_napalm.plugins.tasks import napalm_get
    from nornir_utils.plugins.tasks.files import write_file
    from veritas.tools import tools

    def backup_config(task, path, host_dirs, set_timestamp=False):
        ...

    def main():
        # init nornir
        devices = 'name__ic=local'
        nr = sot.job.on(devices) \
            .set(username=username, password=password, result='result', parse=False) \
            .init_nornir()

        # run tasks
        result = nr.run(
                name="backup_config", 
                task=backup_config, 
                path=backup_dir,
                host_dirs=local_config_file.get('backup',{}).get('individual_hostdir',True)
        )

        # analyze results and log to journal (if uuid is set)
        analysis = tools.analyze_nornir_result(result)
