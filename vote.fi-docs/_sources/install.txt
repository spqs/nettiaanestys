Installation
============

This document contains instructions on building and running the voting
application for development / demo purposes. They are not suitable for a
production deployment.


System installation
-------------------

This section describes the OS level installation procedure for a Linux server.
It is written for a Ubuntu 12.04.2 LTS server but should be easily modified for
any modern Linux distribution.

Required packages
'''''''''''''''''

The application requires the following components

    * C/C++ compilation environment
    * Python 2.7 with development headers
    * Memcached daemon
    * MySQL server
    * MySQL client libraries with development headers

These can be installed with the following command:

.. code-block:: sh

    $ sudo apt-get install build-essential python2.7-dev memcached \
    mysql-server-5.5 libmysqlclient-dev python-virtualenv unzip libmemcached-dev


Application installation
------------------------

The application is assembled using a software build system named
`Buildout <http://www.buildout.org/>`_. Buildout uses a INI-like configuration
file to describe the application environment.


Initialize customer environment
'''''''''''''''''''''''''''''''

Unpack the ``vote.fi-1.0.zip`` archive.

.. code-block:: sh

    $ unzip vote.fi-1.0.zip
    $ cd vote.fi
    $ virtualenv --no-site-packages .

The build system itself needs to be bootstrapped first. This is done by running
the ``bootstrap.py`` script which will download and install the buildout
command.

.. code-block:: sh

    $ ./bin/python bootstrap.py
    Creating directory '.../vote.fi/bin'.
    Creating directory '.../vote.fi/parts'.
    Creating directory '.../vote.fi/eggs'.
    Creating directory '.../vote.fi/develop-eggs'.
    Generated script '.../vote.fi/bin/buildout'.

Assemble the application
------------------------

The application is assembled by running the ``buildout`` script we installed in
the previous step. The ``buildout`` command reads its configuration from the
``buildout.cfg`` file.

.. code-block:: sh

    $ ./bin/buildout

Running the command will download all the dependencies, will take some time
when run for the first time and produces a lot of console output. If the process
hangs it can be terminated and re-run.

.. note::

    The buildout process is dependent on external services such as the Python
    Package Index (http://pypi.python.org) and may fail if these are not
    available.


Configure MySQL database
------------------------

To set up the database for the application you need to do the following

    #. Create a MySQL user
    #. Create the database
    #. Grant the user the required permissions

In the following example we will create a database named ``vote`` and a user
account ``vote`` which will have the required permissions for that database. We
will also limit the access for the ``vote`` user to localhost only. The
application does not depend on any particular choice of names for the database
or user.

.. code-block:: sh

    $ mysql -u root -p
    mysql>

.. code-block:: sql

    CREATE USER 'vote'@'localhost' IDENTIFIED BY 'secret_password';
    GRANT ALL ON vote.* TO 'vote'@'localhost';
    CREATE DATABASE vote;

Verify that you can access the database with the user

.. code-block:: sh

    $ mysql -u vote -p vote


Run test suite
--------------

The application comes with a comprehensive test suite which can be used to
verify that the application works correctly.

.. code-block:: sh

    $ ./bin/nosetests -v src/NuvaVaalit


Configure the application
-------------------------

The application is configured using an INI-style configuration file. An example
configuration is provided in an ``example.ini`` file located in the root of the
buildout directory.

Open up the ``example.ini`` file in an editor and verify at least the following
options.

.. _app-nuvavaalit:

[app:nuvavaalit] section
''''''''''''''''''''''''

``sqlalchemy.url``

    This controls the database the application will use. The database connection
    is defined as an URL using a `RFC-1738 <http://www.ietf.org/rfc/rfc1738.txt>`_
    -style string, e.g.::

        mysql://<username>:<password>@<hostname>/<database>?<options>

    Assuming the database, user and password we created in the example above we
    would configure the database connection string as::

        mysql://vote:secret_password@localhost/vote?charset=utf8

``session.url``

    This controls the Memcached daemon used to store session data for the
    application. The address is configured as a
    ::

        <ip-addr>:<port>

    string.

``session.secure``

    If you are serving the application using SSL/TLS you should set this option
    to ``true``. This will instruct the browser to send the session cookie only
    over an established TLS connection. Otherwise leave the value at ``false``.


``nuvavaalit.num_selected_candidates``

    Determines the number of candidates that get elected.

``nuvavaalit.election_period``

    Determines the election time period. This effectively controls the mode the
    application functions in. Before the election period the application
    displays the front page with banners and allows browsing of the candidate
    list. During the election period the front page is replaced with a login
    page and voting is possible for authenticated users. After the election
    period the results are available.

    Example::

        nuvavaalit.election_period =
            2012-10-21 00:00
            2012-10-22 20:00

``nuvavaalit.show_all_results``

    Determines whether voting results are shown for all candidates or only for
    those that got elected.

.. _server-main:

[server:main] section
'''''''''''''''''''''

``host``

    This is the network interface which the application binds its HTTP server
    to. It is recommended that the host be configured to an interface which is
    not directly accessible from outside (e.g. localhost or a private network
    address).

``port``

    This is the TCP port the application binds to and receives HTTP requests at.

``threads``

    The number of threads used to serve incoming requests.


Set up an example voting
------------------------

A voting requires the database to be populated with both candidates and voters.
To generate testing data use the following commands.

.. code-block:: sh

    $ ./bin/populate_candidates example.ini src/NuvaVaalit/data/test-candidates.csv
    $ ./bin/populate_test_users example.ini

This will populate the database with dummy candidates and generates ten user
accounts named "user1", "user2", etc. The password for all test accounts is
"testi".

After voting a user account is no longer available for use. You can reset the
election by truncating the application database tables or simply deleting them.
The application will recreate them automatically when started.

.. code-block:: sh

    $ mysql -u root -p vote
    mysql>

.. code-block:: sql

    DROP TABLE votes;
    DROP TABLE votinglog;
    DROP TABLE voters;
    DROP TABLE candidates;


Start the application process
-----------------------------

The application server is run using the ``pserve`` command::

    $ ./bin/pserve example.ini

Once running, the application can be accessed at http://localhost:6543.
