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


## Reset the database

Make sure you installed the [`requirements-dev.txt`](./requirements/requirements-dev.txt). And `django_extensions` is in `INSTALLED_APPS` in your settings file (i.e. `settings.py`).

```bash
(pipeline_env)$: ./manage.py reset_db && ./manage.py migrate
```
