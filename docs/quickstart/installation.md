<!-- markdownlint-disable MD046 -->
# Installation

This document provides instructions on installing the VAST Pipeline for local use.

The VAST Pipeline consists of 3 main components that require installation:

1. a PostgreSQL database,
2. a [Django](https://www.djangoproject.com){:target="_blank"} application,
3. a front-end website.

The instructions have been tested on Debian/Ubuntu and macOS.

## PostgreSQL

We recommend using a [Docker](https://www.docker.com/){:target="_blank"} container for the database rather than installing the database system-wide.

Steps:

1. Install Docker. Refer to [the official documentation](https://docs.docker.com/install/){:target="_blank"}, and for Ubuntu users to [this](https://docs.docker.com/install/linux/docker-ce/ubuntu/){:target="_blank"}. Remember to add your user account to the `docker` group [official docs](https://docs.docker.com/install/linux/linux-postinstall/){:target="_blank"}, by running:

    ```console
    sudo groupadd docker
    sudo usermod -aG docker $USER
    ```

2. Create a PostgreSQL container. The VAST Pipeline requires a PostgreSQL database with the [Q3C](https://github.com/segasai/q3c){:target="_blank"} plugin to enable special indexing on coordinates and fast cone-search queries. We have prepared a Docker image based on the latest PostgreSQL image that includes Q3C <ghcr.io/marxide/postgres-q3c>. Start a container using this image by running the command below, replacing `<container-name>` with a name of your choice (e.g. vast-pipeline-db) and `<password>` with a password of your choice which will be set for the default `postgres` database superuser account.

    ```console
    docker run --name <container-name> --env POSTGRES_PASSWORD=<password> --publish-all --detach ghcr.io/marxide/postgres-q3c:latest
    ```

    The `--publish-all` option will make the PostgreSQL server port 5432 in the container accessible on a random available port on your system (the host). The `--detach` option instructs Docker to start the container in the background rather than taking over your current shell. Verify that the container is running and note the host port that `5432/tcp` is published on by running `docker ps`, e.g. in the example below, the host port is `55002`.

    ```console
    docker ps
    CONTAINER ID   IMAGE                                 COMMAND                  CREATED         STATUS         PORTS                     NAMES
    8ff553add2ed   ghcr.io/marxide/postgres-q3c:latest   "docker-entrypoint.s…"   4 seconds ago   Up 3 seconds   0.0.0.0:55002->5432/tcp   vast-pipeline-db
    ```

The database server should now be running in a container on your machine.

!!! tip
    To stop the database server, simply stop the container with the following command

    ```console
    docker stop <container-name or container-id>
    ```

    You can start an existing stopped container with the following command

    ```console
    docker start <container-name or container-id>
    ```

    Note that `docker run` and `docker start` are not the same. `docker run` will _create_ and start a container from an image; `docker start` will start an existing stopped container. If you have previously created a VAST Pipeline database container and you wish to reuse it, you want to use `docker start`. You will likely need to restart the container after a system reboot.

## Python Environment

We strongly recommend installing the VAST Pipeline in an isolated virtual environment (e.g. using [Miniconda](https://docs.conda.io/en/latest/miniconda.html){:target="_blank"}, [Virtualenv](https://virtualenv.pypa.io/en/latest/){:target="_blank"}, or [venv](https://docs.python.org/3/library/venv.html){:target="_blank"}). This will keep the rather complex set of dependencies separated from the system-wide Python installation.

1. Create a new Python environment using your chosen virtual environment manager and activate it. For example, Miniconda users should run the following command, replacing `<environment-name>` with an appropriate name (e.g. pipeline-env):

    ```console
    conda create --name <environment-name> python=3.8
    conda activate <environment-name>
    ```

    !!! note
        All further installation instructions will assume you have activated your new virtual environment. Your environment manager will usually prepend the virtual environment name to the shell prompt, e.g.

        ```console
        (pipeline-env)$ ...
        ```

2. Clone the pipeline repository <https://github.com/askap-vast/vast-pipeline> and change into the repo directory.

    ```console
    git clone https://github.com/askap-vast/vast-pipeline.git
    cd vast-pipeline
    ```

    !!! warning
        **Do not** change the the repo folder name, e.g. `git clone https://github.com/askap-vast/vast-pipeline.git my-pipeline-local-dev`

3. (Optional) Checkout the version you want to install. Currently, the repo will have cloned the latest code from the _master_ branch. If you require a specific version, checkout the appropriate version [tag](https://github.com/askap-vast/vast-pipeline/tags){:target="_blank"} into a new branch e.g. for version 0.2.0

    ```console
    git checkout -b <new-branch-name> 0.2.0
    ```

4. Install non-Python dependencies. Some of the Python dependencies required by the pipeline depend on some non-Python libraries. These can also be installed by Miniconda, otherwise they are best installed using an appropriate package manager for your operating system e.g. `apt` for Debian/Ubuntu, `dnf` for RHEL 8/CentOS 8, [Homebrew](https://brew.sh){:target="_blank"} for macOS. The dependencies are:

    === "Miniconda"

        * libpq
        * graphviz

        Both are available on the [conda-forge](https://conda-forge.org){:target="_blank"} channel. They are also specified in the environment file `requirements/environment.yml` which can be used to install the required packages into an activated conda environment with the following command

        ```console
        conda env update -f requirements/environment.yml
        ```

    === "Debian/Ubuntu"

        * libpq-dev
        * libgraphviz-dev

    === "RHEL/CentOS"

        * libpq-devel
        * graphviz-devel

        !!! note "CentOS users"
            You may need to enable the PowerTools repository to install `graphviz-devel`.

            ```console
            dnf install dnf-plugins-core
            dnf config-manager --set-enabled powertools
            ```

    === "Homebrew"

        * libpq
        * graphviz

5. Install the pipeline and it's Python dependencies.

    ```console
    pip install .
    ```

    !!! warning
        Don't forget the `.` at the end of the above command. It instructs `pip` that the root directory of the package to install is the current directory.

    !!! tip
        If you are intending to deploy an instance of the pipeline onto a server, you may also want to install the recommended production extras with `pip install .[prod]`. However, note that these are recommendations only and there are other alternative packages that may work just as well.

    !!! tip
        If you intend to contribute to development of the pipeline, you will need the Python dependency management tool [Poetry](https://python-poetry.org){:target="_blank"}. See the [development guidelines](../developing/localdevenv.md).

## Front-End Assets Quickstart

In order to install and compile the front-end website assets (modules like js9 and bootstrap, as well as minification of JS and CSS files) you need a recent version of [NodeJS](https://nodejs.org/){:target="_blank"} installed.

### Installation of NodeJS

If you are using Miniconda and installed the `requirements/environment.yml` file as shown above, then NodeJS is already installed. Otherwise, we recommend following the instructions on the NodeJS [downloads page](https://nodejs.org/en/download/){:target="_blank"} for your OS (there are many installation options).

### Setting up the front-end assets

In order to set up the front end assets, run:

```console
npm ci && npm start
```

!!! note
    Ensure you are still in the root of the repo before running the command above. The `npm ci` command ("clean install") will remove all previous node modules and install all the dependencies from scratch. The `npm start` command will run the default `gulp` "task" which, among other things, compiles Sass into CSS, minifies CSS and JS files, and copies these files into the `static/vendor` folder. For more details of compilation of frontend assets (e.g. single tasks), and front-end developement set up read the [Front End Developing Guidelines](../developing/localdevenv.md#frontend-assets-management-and-guidelines).

!!! bug
    When `npm start` or `npm run start` was run in a Ubuntu 20.04 LTS (containerised environment), for some unknown reasons, both commands failed with the following error.

    ```console
    [12:48:19] 'js9Make' errored after 7.67 ms
    [12:48:19] Error: spawn make ENOENT
        at Process.ChildProcess._handle.onexit (internal/child_process.js:267:19)
        at onErrorNT (internal/child_process.js:469:16)
        at processTicksAndRejections (internal/process/task_queues.js:84:21)
    [12:48:19] 'default' errored after 2.63 s
    npm ERR! code ELIFECYCLE
    npm ERR! errno 1
    npm ERR! vast-pipeline@99.99.99-dev start: `gulp default`
    npm ERR! Exit status 1
    npm ERR!
    npm ERR! Failed at the vast-pipeline@99.99.99-dev start script.
    npm ERR! This is probably not a problem with npm. There is likely additional logging output above.
    npm ERR! A complete log of this run can be found in:
    npm ERR!     /home/vast/.npm/_logs/2020-10-06T01_48_19_215Z-debug.log
    ```

    The way around for this issue is unorthodox. The following steps were followed to overcome the issue:

    ```console
    cd node_modules/js9/
    ./configure
    make
    make install
    cd ~/vast-pipeline/  ## (to comeback to the root folder of the project)
    npm install
    ```

    That somehow solved the issue mentioned above.

---

Done! Now go to [Vast Pipeline Configuration](configuration.md) file to see how to initialize and run the pipeline. Otherwise if you intend on developing the repo open the [Contributing and Developing Guidelines](../developing/intro.md) file for instructions on how to contribute to the repo.
