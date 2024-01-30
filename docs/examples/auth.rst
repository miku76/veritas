*******************************
Encrypt / decrypt your Password
*******************************

You can encrypt your password as follows:

.. code-block:: python

    import veritas.auth
    encrypted_password = veritas.auth.encrypt(password=password, 
                                              salt=salt, 
                                              encryption_key=encryption_key, 
                                              iterations=int(iterations))

You can decrypt your password as follows:

.. code-block:: python

    import veritas.auth
    clear_password = veritas.auth.decrypt(token=token, 
                                          salt=salt, 
                                          encryption_key=encryption_key, 
                                          iterations=int(iterations))

The toolkit uses profiles to decrypt password. It loads your profile and decrypts the password.

.. code-block:: python

    from veritas.tools import tools
    username, password = tools.get_username_and_password(
        profile_config,
        args.profile,
        args.username,
        args.password)

.. note::

    When encrypting and decrypting the password, the three parameters salt, 
    encryption key and iterations must match.
    The veritas toolkit uses a salt.yaml file in your personal directory 
    (~user/.veritas/miniapps/app) for this purpose.