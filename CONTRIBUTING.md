# VAST Pipeline - Developing Notes

This document explains how to contribute to the project code base.

A very exahustive set of general guidelines can be follow [here](https://github.com/apache/incubator-superset/blob/master/CONTRIBUTING.md), but I think the following will suffice for our purpose.

## Table of Contents

- [Terminology](#terminology)
- [Pull Request Guideline](#pull-request-guideline)
- [Releasing Guidelines](#releasing-guidelines)
- [Solving your `models.py`/migrations issues](#solving-your-modelspymigrations-issues)
	- [1. You modify `models.py`](#1-you-modify-modelspy)
	- [2. Someone else modified `models.py` and you pull the changes](#2-someone-else-modified-modelspy-and-you-pull-the-changes)
- [Removing/Clearing Data](#removingclearing-data)
  - [Reset the database](#reset-the-database)
  - [Clearing Run Data](#clearing-run-data)
- [Run Tests](#run-tests)

## Terminology

* Pipeline run (or 'Run') -> Pipeline run instance, also referred as `run, p_run, piperun, pipe_run, ...` in the code
* Measurement -> the extracted measurement from the source finder of a single astrophysical source from an image, referred in the code as `measurement(s), meas, ...`
* Source -> A collection of single measurements for the same astrophysical source, referred as `src, source, ...` in the code

## Pull Request Guideline
First consider
>opening an issue before creating/issuing the PR.

So we can separe problems from solutions.

1. Open an issue (e.g. `My issue blah`, GitHub will assign a id e.g. `#123`).
2. Branch off `master` by naming your branch `fix-#123-my-issue-blah` (keep it short please).
3. Do your changes.
4. Run one or more pipeline run on full images to test functionality.
5. Run test locally with `./manage.py test pipeline` (there are few tests, mostly not working).
6. Run the webserver and check the functionality.
7. Commit and issue the PR.

PRs not branched off master will be __rejected__!.

## Releasing Guidelines

In to order to make a release, please follow these steps (example: making the `0.1.0` release):

1. Make sure that every new feature and PR will be merged to master, before continuing with the releasing process.
2. Update the [`CHANGELOG.md`](./CHANGELOG.md) on `master` directly (only admin can and need to force-push the changes) with the list of changes. An example of format can be found [here](https://github.com/apache/incubator-superset/blob/master/CHANGELOG.md).
3. The `0.1.X` branch will be updated by merging `master` into `0.1.X`.
4. Branch off `0.1.X` and call it `0.1.1`, then change the `package.json` with the version of the release, commit and tag the commit. Push commit and tag to origin.
5. Make a release in GitHub using that tag.

__NOTE__: keep the version on `master` branch to something like 99.99.99dev and in `0.1.X` branch to something like 0.1.99dev. In the release branch, change only the version in [`package.json`](./package.json).

## Solving your `models.py`/migrations issues

First of all the `makemigrations` command must be run only if you modified the `models.py` or you pull down changes (i.e. `git pull`) that modify `models.py`. So please refer to the cases below:

### 1. You modify `models.py`

In this case there are 2 situations that arise:

1. You currently don't have a production environment and/or you are comfortable in dropping all the data in the database. In this case, you don't need to update the production environment with multiple migration files even though Django docs promote making as many migrations as you need to ([see Django migration guidelines](https://docs.djangoproject.com/en/3.0/topics/migrations/#squashing-migrations)). For such reasons please consider doing the following steps:

   1.1. Make your changes to `models.py`.

   1.2. Remove all the migration files including `0002_q3c.py`.

   1.3. Run `./manage.py makemigrations`. This  will generate a __NEW__ `0001_initial.py` file.

   1.4. Commit the new migraton file `0001_initial.py` as well as `models.py` within a single commit, and add an appropriate message (e.g. add field X to model Y). __DO NOT__ commit the removal of `0002_q3c.py`.

   1.5. Get back the Q3C migration file `git checkout pipeline/migrations/0002_q3c.py`.

2. You currently have a production environment and/or you do not want to lose all the data in the database. In this situation, you need to be careful not to mess up with the producation database, so please consider doing the following steps:

   2.1. Make a copy ("dump") of the production database as it is, e.g. (by logging remotely to the server) `pg_dump -h DBHOST_PROD -p DBPORT_PROD -U DBUSER_PROD -Fc -o DBNAME_PROD > prod-backup-$(date +"%F_%H%M").sql`.

   2.2. Upload the copy to your local development database, e.g. `pg_restore -h DBHOST_DEV -p DBPORT_DEV --verbose --clean --no-acl --no-owner -U DBUSER_DEV -d DBNAME_DEV prod-backup.sql`.

   2.3. Make your changes to `models.py`.

   2.4. Run `./manage.py makemigrations` with optional but strongly recommended `-n 'my_migration_name'`. This will generate a new migration file `000X_my_migration_name.py` where X is incremented by 1 with respect the last migration file.

   2.5. Commit the new migraton file `000X_my_migration_name.py` as well as `models.py` within a single commit, and add an appropriate message (e.g. add field X to model Y)

__NOTE__: do not modify the `0002_q3c.py` file as it relates to migration operations for using Q3C plugin and related functions!

### 2. Someone else modified `models.py` and you pull the changes

Situation:

```bash
~/vast-pipeline [master]$ git fetch && git pull
Updating abc123..321cba
Fast-forward
 pipeline/models.py | 4 +++-
 pipeline/migrations/0001_initial.py | 5 ++++-
 2 file changed, 9 insertions(+), 2 deletions(-)
```

You realise that you are in this situation when:

- In the command above you see changes (i.e. `+` or `-`) in `models.py` and/or in migrations (i.e. `XXXX_some_migration.py`)

- Running the webserver, a message reports
```bash
You have unapplied migrations;
your app may not work properly until they are applied.
Run 'python manage.py migrate' to apply them.
```

- Running the pipeline you have errors related to the database models

Solutions to such scenario:

If you don't mind losing all the data in your database just follow the [Reset the database](#reset-the-database) instructions to drop all the data. But if you want to keep your data, you have to fix these changes by trying running `makemigrations` and `migrate`. But ideally you should follow the following steps:

1. Identify the previous commit before pulling the changes (when your migration and model files were working):

```bash
~/vast-pipeline [master]$ git show -1 pipeline/models.py #OR
~/vast-pipeline [master]$ git show -2 pipeline/models.py #OR
~/vast-pipeline [master]$ git show -1 pipeline/migrations/XXXX_my_migration.py
```

Or even better

```bash
~/vast-pipeline [master]$ git log -p pipeline/models.py
```

2. Take note of the commit hash of the old changes (i.e. before pulling down the new changes). Checkout __ONLY__ your old migration files, for example like this:

```bash
~/vast-pipeline [master]$ git checkout 37cabac84785742437927c785b63a767aa8ac5ff pipeline/migrations/0001_initial.py
```

3. Make the migrations `./manage.py makemigrations && ./manage.py migrate`

4. Run the pipeline and the webserver to see that everything is working fine

5. Squash the migrations using [Django migration guidelines](https://docs.djangoproject.com/en/3.0/topics/migrations/#squashing-migrations)

6. Continue with the normal development cycle (i.e. branch off master, do changes, commit everything, _including your changes in the models/migrations even done with the squashing!_)

## Removing/Clearing Data

The following sub-sections show how to completely drop every data in the database and how to remove only the data related to one or more pipeline runs.

### Reset the database

Make sure you installed the [requirements `dev.txt`](./requirements/dev.txt). And `django_extensions` is in `EXTRA_APPS` in your setting configuration file `.env` (e.g. `EXTRA_APPS=django_extensions,another_app,...`).

```bash
(pipeline_env)$ ./manage.py reset_db  && ./manage.py migrate
# use the following for no confirmation prompt
(pipeline_env)$ ./manage.py reset_db --noinput  && ./manage.py migrate
```

### Clearing Run Data

It is convenient removing the data belonging to one or more pipeline run, while developing the code base. This is particularly useful to save time and don't upload the image data along with the measurements. The data related to the pipeline are the Sources, Associations, Forced extractions entries in database and the parquet files in the respective folder. By default the command will keep the run folder with the config and the log files.

```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my-pipe-run
```

To clear more than one run:

```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my-pipe-run1 my-pipe-run2 path/to/my-pipe-run3
```

The command accept both a path or a name of the pipeline run(s). To remove __all__ the runs, issue:

```bash
(pipeline_env)$ ./manage.py clearpiperun clearall
```

The command to keep the parquet files is:

```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my-pipe-run --keep-parquet
```

The remove completely the pipeline folder

```bash
(pipeline_env)$ ./manage.py clearpiperun path/to/my-pipe-run --remove-all
```

## Run Tests

Test are found under the folder [tests](./vast_pipeline/tests/). Have a look and feel free to include new tests.

Run the tests with the following:

To run all tests:
```bash
(pipeline_env)$ ./manage.py test
```

To run one test file or class, use:
```bash
(pipeline_env)$ ./manage.py test <path/to/test>
```
for example, to run the test class `CheckRunConfigValidationTest` located in [`test_runpipeline.py`](./vast_pipeline/tests/test_runpipeline.py), use:
```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_runpipeline.CheckRunConfigValidationTest
```
to run the tests located in [`test_webserver.py`](./vast_pipeline/tests/test_webserver.py), use:
```bash
(pipeline_env)$ ./manage.py test vast_pipeline.tests.test_webserver
```

Regression tests located in [`test_regression.py`](./vast_pipeline/tests/test_regression.py) requires the use of the VAST_2118-06A field test dataset which is not a part of the repository. This data is downloadable at https://cloudstor.aarnet.edu.au/plus/s/rC6zRShsv42m2ih, use:
```bash
wget https://cloudstor.aarnet.edu.au/plus/s/rC6zRShsv42m2ih
```
place the VAST_2118-06A field test dataset in a folder named `regression-data` inside the [tests](./vast_pipeline/tests/) folder. These regression tests are skipped if the data folder containing the dataset is not present. 

All tests should be run before pushing to master. Running all the tests takes a few minutes, so it is not recommended to run them for every change. 