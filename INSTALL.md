# ASKAP Pipeline Development - Installation Notes

This document explains how to install all the packages that the pipeline needs to run, as well as the PostgreSQL database. Following this documentation should get you started with a good __LOCAL__ development environment, where you can mess up things, but always go back and fix it up.

Note for installs on a Mac, the use of `homebrew` is recommended (https://brew.sh).

## PostgreSQL Installation

I don't recommend installing the database as part of a system package (e.g. `apt-get install postgres`), but instead use docker, which let you mess up things and keep your database installation separated from the system packages, given also that you need to install Python packages for the database to use, but you don't want to confuse them with the Pipeline Python environment.

Steps:

1. Installing docker in your system. Refer to [this official documentation](https://docs.docker.com/install/), and for Ubuntu users to [this](https://docs.docker.com/install/linux/docker-ce/ubuntu/). Remember to add your `user` to the `docker` group [official docs](https://docs.docker.com/install/linux/linux-postinstall/), by running

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
```

2. create your PostgreSQL container: `docker run --name NAME_OF_MyCONTAINER -e POSTGRES_PASSWORD=postgres -p 127.0.0.1:5432:5432 -d postgres`. This will install a PostgreSQL 9.6 container exposing the container internal port 5432 to your system (`127.0.0.1` or `localhost`) at port `5432`. I encourage to change the localhost port (e.g. `5433:5432`) so you know you're are in control! The command setup automatically a user `postgres` with password `postgres` and default database `postgres`. If everything goes well, you see your container up and running by issuing `docker ps`.

```bash
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
afnafnalkfo3        postgres:9.6        "docker-entrypoint.s…"   22 hours ago        Up 22 hours         localhost:5432->5432/tcp   NAME_OF_MyCONTAINER
```

If `localhost` is not passed, the command exposes the port on `0.0.0.0` so other users on the same subnet (e.g. same WiFi access point) can connect to it (I don't recommend it for a local development environment!)

3. Install PostgreSQL dependency [`Q3C`](https://github.com/segasai/q3c):

    a. Connect to the container by running `docker exec -it NAME_OF_MyCONTAINER bash`. That runs `bash` shell as `root` inside the container.

    b. Install the packages, replace XX with the postgres version installed in docker (check version with `psql -U postgres`):

    ```bash
    apt-get update -y && apt-get install -y libssl-dev libkrb5-dev zlib1g-dev make git gcc postgresql-server-dev-XX postgresql-common
    ```
    c. Clone `Q3C` repo and install it:

    ```bash
    git clone https://github.com/segasai/q3c.git
    cd q3c
    make
    make install
    ```

You can disconnect from the container and the database installation should now be complete. You can connect to the database by running the `psql` CLI (Command Line Interface) by installing on your system (e.g. Ubuntu `sudo apt-get install postgres-common` or just `postgresql-client-common`, Mac: `brew install libpq`). Alternatively you can access the CLI by connecting to the container as described above (`docker exec -it NAME_OF_MyCONTAINER bash`). Finally connect to your PostgreSQL instance:

```bash
psql -h localhost -p 5432 -U postgres
```

Output

```bash
psql (YYYY (MYOS YYYY), server XXXX)
Type "help" for help.

postgres=#
```

The command will ask you for the password, please type `postgres`. The password is set by the `POSTGRES_PASSWORD=postgres` environment variable at container initialization, and __CAN'T__ be changed afterward.

As you can see does not matter if the CLI client is for higher PostgreSQL versions, as it still connect to your instance ( e.g. `psql (11.0 (Ubuntu 11.0-2.pgdg18.04+1), server 12.1 (Debian 12.1-1.pgdg100+1))`).

Basic Start/Stop commands are `docker start NAME_OF_MyCONTAINER` and `docker stop NAME_OF_MyCONTAINER`. Remember to start your container after rebooting your machine, if you don't have docker daemon configured to autoload!

## Pipeline Python Environment Installation
I strongly recommend to setup a virtual environment, in which you can then install all these `Python` modules into.
This will avoid conflicts either with the system version of python, or with other code that you have that require different versions of these modules.

Steps:
1. Copy repo link from `Clone or download` button and clone the repository:
```bash
git clone <PASTE REPO LINK> && cd <REPO>
```

2. Setup a `Python >= 3.6` virtual environment. E.g. with `virtualenv`:
```bash
virtualenv -p python3 pipeline_env
```
Otherwise use `Anaconda/conda`:
```bash
conda create -n pipeline_env python=3.6
```

NOTE: you can name the environment whatever you want instead of `pipeline_env`

3. Activate the environment.
```bash
source pipeline_env/bin/activate
```
Otherwise use `Anaconda/conda`:

```bash
conda activate pipeline_env
```

4. Install the development requirements

Note that if you want to install the development requirements, graphviz needs to be installed on your system (Ubuntu: `sudo apt-get install graphviz`, Mac: `brew install graphviz`).

```bash
pip install -r requirements/requirements-dev.txt
```
or with conda (some packages will not be installed properly so check and eventually install them manually, if not with `conda`, with `pip`):
```bash
while read requirement; do conda install --yes $requirement; done < requirements/requirements-dev.txt
while read requirement; do conda install --yes $requirement; done < requirements/requirements.txt
```

Done! Now open the [`README.md`](./README.md) file to see how to initialize and run the pipeline.

