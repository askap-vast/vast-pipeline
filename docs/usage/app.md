# Web App

This section describes how to run the pipeline Django web app/server.

## Starting the Pipeline Web App

Make sure you installed and compiled correctly the frontend assets see [guide](../quickstart/installation.md#front-end-assets-quickstart)

1. Start the Django development web server:

```bash
(pipeline_env)$ ./manage.py runserver
```

2. Test the webserver by pointing your browser at http://127.0.0.1:8000 or http://localhost:8000

The webserver is independent of `runpipeline` and you can use the website while the pipeline commands are running.

## Running a pipeline run via the web server

It is possible to launch the processing of a pipeline run by using the relevant option on the pipeline run detail page. This uses `DjangoQ` to schedule and process the runs and a cluster needs to be set up in order for the runs to process:

1. Check the `Q_CLUSTER` options in [`./webinterface/settings.py`](https://github.com/askap-vast/vast-pipeline/blob/master/webinterface/settings.py). Refer to the [DjangoQ docs](https://django-q.readthedocs.io/en/latest/index.html) if you are unsure on the meaning of any parameters.

2. Launch the cluster using the following command, making sure you are in the pipeline environment:
```
(pipeline_env)$ ./manage.py qcluster
````

If the pipeline is updated then the `qcluster` also needs to be be restarted.
A warning that if you submit jobs before the cluster is set up, or is taken down, then these jobs will begin immediately once the cluster is back online.
