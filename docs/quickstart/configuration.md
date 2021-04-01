<!-- markdownlint-disable MD046 -->
# Configuration

This section describe how to configure your VAST Pipeline installation.

## Pipeline Configuration

The following instructions, will get you started in setting up the database and pipeline configuration.

!!! note
    The commands given in this section, unless otherwise stated, assume that the current directory is the pipeline root and that your pipeline Python environment has been activated.

1. Create a database for the pipeline. If you followed the [installation](installation.md) process, you will have a PostgreSQL Docker container running on your system. Use the provided script `init-tools/init-db.py` script to create a new database for the pipeline. As a security precaution, this script will also create a new database user and set the pipeline database owner to this new user.

    The initialization script requires several input parameters. For usage information, run with the `--help` option:

    ```console
    python init-tools/init-db.py --help
    usage: init-db.py [-h] host port admin-username admin-password username password database-name

    Initialize a PostgreSQL database for VAST Pipeline use. Creates a new superuser and creates a new database owned by the new superuser.

    positional arguments:
    host            database host
    port            database port
    admin-username  database administrator username
    admin-password  database administrator password
    username        username for the new user/role to create for the VAST Pipeline
    password        password for the new user/role to create for the VAST Pipeline
    database-name   name of the new database to create for the VAST Pipeline

    optional arguments:
    -h, --help      show this help message and exit
    ```

    Fill in the parameters as appropriate for your configuration. If you followed the [installation](installation.md) instructions, these would be the details for your PostgreSQL Docker container. Following from the same example in the installation section:

    ```console
    python init-tools/init-db.py localhost 55002 postgres <password> vast <vast-user-password> vastdb
    ```

    !!! info
        Where `<password>` is the superuser password that was passed to `docker run`, and `<vast-user-password>` is a new password of your choice for the new `vast` database user.

        You may change the values for the username and database-name, the above is just an example.

    If everything went well the output should be:

    ```console
    Creating new user/role vast ...
    Creating new database vastdb ...
    Done!
    ```

2. Copy the setting configuration file template and modify it with your desired settings (see [defaults](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/.env.template){:target="_blank"}).

    ```console
    cp webinterface/.env.template webinterface/.env
    ```

3. Set the database connection settings in the `webinterface/.env` file by modifying `DATABASE_URL` (for URL syntax see [this link](https://django-environ.readthedocs.io/en/latest/#tips){:target="_blank"}). For example:

    ```bash
    DATABASE_URL=psql://vast:<vast-user-password>@localhost:55002/vastdb
    ```

    !!! note
        The connection details are the same that you setup during the [installation](installation.md). The database/user names must not contain any spaces or dashes, so use the underscore if you want, e.g. `this_is_my_db_name`.

4. Create the pipeline database tables. The `createcachetable` command creates the cache tables required by DjangoQ.

    ```bash
    python manage.py migrate
    python manage.py createcachetable
    ```

5. Create the pipeline data directories. The pipeline has several directories that can be configured in `webinterface/.env`:

    * `PIPELINE_WORKING_DIR`: location to store various pipeline output files.
    * `SURVEYS_WORKING_DIR`: location of reference survey catalogues, e.g. NVSS, SUMSS.
    * `RAW_IMAGE_DIR`: default location that the pipeline will search for input images and catalogues to ingest during a pipeline run. Data inputs can also be defined as absolute paths in a pipeline run configuration file, so this setting only affects relative paths in the pipeline run configuration.
    * `HOME_DATA_DIR`: additional location to search for input images and catalogues that is relative to the user's home directory. Intended for multi-user server deployments and unlikely to be useful for local installations.

    While the default values for these settings are relative to the pipeline codebase root (i.e. within the repo), we recommend creating these directories outside of the repo and updating the `webinterface/.env` file appropriately with absolute paths. For example, assuming you wish to create these directories in `/data/vast-pipeline`:

    ```console
    mkdir -p /data/vast-pipeline
    mkdir /data/vast-pipeline/pipeline-runs
    mkdir /data/vast-pipeline/reference-surveys
    mkdir /data/vast-pipeline/raw-images
    mkdir /data/vast-pipeline/vast-pipeline-extra-data
    ```

    and update the `webinterface/.env` file with:

    ```bash
    PIPELINE_WORKING_DIR=/data/vast-pipeline/pipeline-runs
    SURVEYS_WORKING_DIR=/data/vast-pipeline/reference-surveys
    RAW_IMAGE_DIR=/data/vast-pipeline/raw-images
    HOME_DATA_DIR=/data/vast-pipeline/vast-pipeline-extra-data
    ```

## Authentication

The pipeline supports two authentication methods: GitHub Teams, intended to multi-user server deployments; and local Django administrator. For a single-user local installation, we recommend creating a Django superuser account.

### Django superuser

Create a Django superuser account with the following command and follow the interactive prompts.

```console
python manage.py createsuperuser
```

This account can be used to log into the Django admin panel once the webserver is running (see [Starting the Pipeline Web App](../adminusage/app.md#starting-the-pipeline-web-app)) by navigating to <https://localhost:8000/pipe-admin/>. Once logged in, you will land on the Django admin page. Navigate back to the pipeline homepage <http://localhost:8000/> and you should be authenticated.

## Data Exploration via Django Web Server

You can start the web app/server via the instructions provided in [Starting the Pipeline Web App](../adminusage/app.md#starting-the-pipeline-web-app).
