Installation Notes
==================

This document explains how to install all the packages that the pipeline needs to run, as well as the PostgreSQL database. Following this documentation should get you started with a good **LOCAL** development environment, where you can mess up things, but always go back and fix it up.

Note for installs on a Mac, the use of ``homebrew`` is recommended (https://brew.sh).

.. contents:: **Table of Contents**
   :depth: 2
   :local:

PostgreSQL
----------

I don't recommend installing the database as part of a system package (e.g. ``apt-get install postgres``), but instead use docker, which let you mess up things and keep your database installation separated from the system packages. In this way you can easily destroy and re-create the database without messing up your OS installed packages.

Steps:

1. Installing docker in your system. Refer to `this official documentation <https://docs.docker.com/install/>`_, and for Ubuntu users to `this <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_. Remember to add your ``user`` to the ``docker`` group `official docs <https://docs.docker.com/install/linux/linux-postinstall/>`_, by running

.. code-block:: bash

    sudo groupadd docker
    sudo usermod -aG docker $USER

2. create your PostgreSQL container: ``docker run --name NAME_OF_MyCONTAINER -e POSTGRES_PASSWORD=postgres -p 127.0.0.1:5432:5432 -d postgres``. This will install a PostgreSQL 12.1 container exposing the container internal port 5432 to your system (``127.0.0.1`` or ``localhost``) at port ``5432``. I encourage to change the localhost port (e.g. ``5433:5432``) so you know you're are in control! The command setup automatically a user ``postgres`` with password ``postgres`` and default database ``postgres``. If everything goes well, you see your container up and running by issuing ``docker ps``.

.. code-block:: bash

    CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
    afnafnalkfo3        postgres:12.1        "docker-entrypoint.s…"   22 hours ago        Up 22 hours         localhost:5432->5432/tcp   NAME_OF_MyCONTAINER

If ``localhost`` is not passed, the command exposes the port on ``0.0.0.0`` so other users on the same subnet (e.g. same WiFi access point) can connect to it (I don't recommend it for a local development environment!)

3. Install PostgreSQL dependency `Q3C <https://github.com/segasai/q3c>`_:

   a. Connect to the container by running ``docker exec -it NAME_OF_MyCONTAINER bash``. That runs ``bash`` shell as ``root`` inside the container.

   b. Install the packages, replace XX with the postgres version installed in docker (check version with ``psql -U postgres``): ::

   .. code-block:: bash

       apt-get update -y && apt-get install -y libssl-dev \
        libkrb5-dev zlib1g-dev make git gcc postgresql-server-dev-XX postgresql-common

   c. Clone ``Q3C`` repo and install it:

   .. code-block:: bash

      git clone https://github.com/segasai/q3c.git
      cd q3c
      make
      make install

You can disconnect from the container and the database installation should now be complete. You can connect to the database by running the ``psql`` CLI (Command Line Interface) by installing on your system (e.g. Ubuntu ``sudo apt-get install postgres-common`` or just ``postgresql-client-common``, Mac: ``brew install libpq``). Alternatively you can access the CLI by connecting to the container as described above (``docker exec -it NAME_OF_MyCONTAINER bash``). Finally connect to your PostgreSQL instance:

.. code-block:: bash

    psql -h localhost -p 5432 -U postgres

Output:

.. code-block:: bash

    psql (YYYY (MYOS YYYY), server XXXX)
    Type "help" for help.

    postgres=#

The command will ask you for the password, please type ``postgres``. The password is set by the ``POSTGRES_PASSWORD=postgres`` environment variable at container initialization, and **CAN'T** be changed afterward.

As you can see does not matter if the CLI client is for higher PostgreSQL versions, as it still connect to your instance ( e.g. ``psql (11.0 (Ubuntu 11.0-2.pgdg18.04+1), server 12.1 (Debian 12.1-1.pgdg100+1))``).

Basic Start/Stop commands are ``docker start NAME_OF_MyCONTAINER`` and ``docker stop NAME_OF_MyCONTAINER``. Remember to start your container after rebooting your machine, if you don't have docker daemon configured to autoload!


Pipeline Python Environment
---------------------------

I strongly recommend to setup a virtual environment, in which you can then install all these `Python` modules into.
This will avoid conflicts either with the system version of python, or with other code that you have that require different versions of these modules.

Steps:

1. Install OS requirements:

* gcc
* python3-dev
* libpq-dev
* libgraphviz-dev (for development requirements)

For Ubuntu:

.. code-block:: bash

    sudo apt-get install python3-dev libpq-dev libgraphviz-dev

2. Copy repo link from `Clone or download` button and clone the repository:

.. code-block:: bash

    git clone <PASTE REPO LINK> && cd <REPO>

**NOTE**: DO NOT change the the folder name, e.g. `git clone https://github.com/askap-vast/vast-pipeline.git my-pipeline-local-dev`

3. Setup a ``Python >= 3.6`` virtual environment. E.g. with ``virtualenv``:

.. code-block:: bash

    virtualenv -p python3 pipeline_env

Otherwise use ``Anaconda/conda``:

.. code-block:: bash

    conda create -n pipeline_env python=3.6

**NOTE**: you can name the environment whatever you want instead of `pipeline_env`

4. Activate the environment.

.. code-block:: bash

    source pipeline_env/bin/activate

Otherwise use ``Anaconda/conda``:

.. code-block:: bash

    conda activate pipeline_env

5. Install the development requirements

Note that if you want to install the development requirements, graphviz needs to be installed on your system (Ubuntu: ``sudo apt-get install graphviz``, Mac: ``brew install graphviz``).

.. code-block:: bash

    (pipeline_env)$ pip install -r requirements/dev.txt

or with conda (some packages will not be installed properly so check and eventually install them manually, if not with ``conda``, with ``pip``):

.. code-block:: bash

    (pipeline_env)$ while read requirement; do conda install --yes $requirement; done < requirements/dev.txt
    (pipeline_env)$ while read requirement; do conda install --yes $requirement; done < requirements/base.txt


Pipeline Front End Assets Quickstart
------------------------------------

In order to install and compile the frontend assets (modules like js9 and bootstrap, as well as minification of JS and CSS files) you need a recent version of `node` with `npm` installed.


Installation of `Node` and `npm`
++++++++++++++++++++++++++++++++

We recommend install an node version manager like `nvm <https://github.com/nvm-sh/nvm>`_. Check the links for the latest version, but the time of writing, the following command will install ``nvm`` and ``node``:

.. code-block:: bash

    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash
    command -v nvm && nvm install --lts || echo "nvm not found"

That would install ``node v12.17.0`` at the time of writing.

Setting up the front end assets
+++++++++++++++++++++++++++++++

In order to set up the front end assets, run:

.. code-block:: bash

    $ pwd
    /PATH/TO/REPO/vast-pipeline
    $ npm ci && npm start


**NOTE**: make sure you are in the root of the repo, as shown above. That command "clean install" all the dependencies, copies files into the ``static/vendor`` folder and minified CSS and JS files. For more details of compilation of frontend assets (e.g. single tasks), and developement set up read the [Front End `README.md`](./static/README.md).

----

Done! Now open the [`README.md`](./README.md) file to see how to initialize and run the pipeline. Otherwise if you intend on developing the repo open the [`CONTRIBUTING.md`](./CONTRIBUTING.md) file for instructions on how to contribute to the repo.
