# Deployment

## Production System
This section describes a simple deployment without using Docker containers, assuming the use of [WhiteNoise](http://whitenoise.evans.io/en/stable/) to serve the static files. It is possible to serve the static files using other methods (e.g. Nginx). And in the future it is possible to upgrade the deployment stack using Docker container and Docker compose (we foresee 3 main containers: Django, Dask and Traefik/Nginx). We recommend in any case reading [Django deployment documentation](https://docs.djangoproject.com/en/3.1/howto/deployment/) for general knowledge.

!!! note
    We assume deployment to a __UNIX server__.

The following steps describes how to set up the Django side of the production deployment, and can be of reference for a future Dockerization. They assumed you have `SSH` access to your remote server and have `sudo` priviledges.

### Web App Deployment

1. Clone the repo in a suitable path, e.g. `/opt/`.

    ```bash
    $ cd /opt && sudo git clone https://github.com/askap-vast/vast-pipeline
    ```

2. Follow the [Installation Instructions](installation.md). We recommend installing the Python virtual environment under the pipeline folder.

    ```bash
    $ cd /opt/vast-pipeline && virtualenv -p python3 pipeline_env
    ```

3. Configure your `.env` files with all the right settings.

4. Check that your server is running fine by changing `DEBUG = True` in the `.env` file.

5. Run Django deployment checklist command to see what are you missing. It is possible that some options are turned off, as implemented in the reverse proxy or load balancer of your server (e.g. `SECURE_SSL_REDIRECT = False` or not set, assumes your reverse proxy redirect HTTP to HTTPS).

    ```bash
    (pipeline_env)$ ./manage.py check --deploy
    ```

6. Build up the static and fix url in JS9:

    ```bash
    (pipeline_env)$ cd /opt/vast-pipeline && npm ci && npm start \
        && npm run js9staticprod && ./manage.py collectstatic -c --noinput
    ```

7. Set up a unit/systemd file as recommended in [Gunicorn docs](https://docs.gunicorn.org/en/latest/deploy.html#systemd) (feel free to use the socket or an IP and port). An example of command to write in the file is (assuming a virtual environment is installed in `venv` under the main pipeline folder):

    ```bash
    ExecStart=/opt/vast-pipeline/venv/bin/gunicorn -w 3 -k gevent \
        --worker-connections=1000 --timeout 120 --limit-request-line 6500 \
        -b 127.0.0.1:8000 webinterface.wsgi
    ```
  __NOTE__: (for future development) the `--limit-request-line` parameter needs to be adjusted for the actual request length as that might change if more parameters are added to the query.

8. Finalise the installation of the unit file. Some good instructions on where to put, link and install the unit file are described in the [Jupyter Hub docs](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html#setup-systemd-service)

### Extra Service(s) Deployment

In order to run a pipeline run from the Web App, the `Django-Q` process need to be started and managed as a service by the OS. In order to do so we recommend building a unit/systemd file to manage the `Django-Q` process, in a similar way of the `gunicorn` process (following the [Jupyter Hub docs](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html#setup-systemd-service)):

```bash
...
WorkingDirectory=/opt/vast-pipeline
ExecStart=/opt/vast-pipeline/venv/bin/python manage.py qcluster
...
```

!!! tip "Tip"
    In the examples above I decided to install the Python virtual enviroment of the pipeline, in `venv` folder under the cloned repository

## Security

By default the settings file has some security parameters that are set when you run the web app in production (`DEBUG = False`), but you can read more in the Django documentation or in this [blog post](https://adamj.eu/tech/2019/04/10/how-to-score-a+-for-security-headers-on-your-django-website/) in which they explain how to get an A+ rating for your web site.
