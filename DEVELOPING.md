# VAST Pipeline Prototype - Developing Notes

This document explains how to contribute to the project code base.

A very exahustive set of general guidelines can be follow [here](https://github.com/apache/incubator-superset/blob/master/CONTRIBUTING.md), but I think the following will suffice for our purpose.

## Pull Request Guideline
1. Branch off `master`
2. Do your changes
3. Commit and issue the PR

PRs not branched off master will be __rejected__!.

Also consider
>opening an issue before creating/issuing the PR.

So we can separe problems from solutions.

## Solving your `models.py`/migrations issues

First of all the `makemigrations` command must be run only if you modified the `models.py` or you pull down changes (i.e. `git pull`) that modify `models.py`. So please refer to the cases below:

### 1) You modify `models.py`

Since this models does not have a production environment that runs 24/7, so you don't need to update the production environment with multiple migration files event though Django docs promote making as many migrations as you need to ([see Django migration guidelines](https://docs.djangoproject.com/en/3.0/topics/migrations/#squashing-migrations)). For such reasons please consider doing the following steps:
1. Make your changes to `models.py`
2. Remove the only migration file `0001_initial.py`
3. Run `./manage.py makemigrations`
4. Commit the 'new' migraton file `0001_initial.py` as well as `models.py` within a single commit, and add an appropriate message (e.g. add field X to model Y)

### 2) Someone else modified `models.py` and you pull the changes

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

## Reset the database

Make sure you installed the [`requirements-dev.txt`](./requirements/requirements-dev.txt). And `django_extensions` is in `INSTALLED_APPS` in your settings file (i.e. `settings.py`).

```bash
(pipeline_env)$: ./manage.py reset_db && ./manage.py migrate
```
