# Pipeline Local Development Environment Guidelines

This section describes how to set up a local development environment more in details.

## Back End

### Installation

The installation instructions are the same as the ones describes in the [Getting Started section](../gettingstarted/installation.md) with one key difference. Rather than installing the Python dependencies with pip, you will need to install and use [Poetry](https://python-poetry.org){:target="_blank"}. After installing Poetry, running the command below will install the pipeline dependencies defined in `poetry.lock` into a virtual environment. The main difference between using Poetry and pip is that pip will only install the dependencies necessary for using the pipeline, whereas Poetry will also install development dependencies required for contributing (e.g. tools to build the documentation).

```console
poetry install
```

!!! note
    Poetry will automatically create a virtual environment if it detects that your shell isn't currently using one. This should be fine for most users. If you prefer to use an alternative virtual environment manager (e.g. Miniconda), you can [prevent Poetry from creating virtual environments](https://python-poetry.org/docs/faq/#i-dont-want-poetry-to-manage-my-virtual-environments-can-i-disable-it){:target="_blank"}. However, even if you are using something like Miniconda, allowing Poetry to manage the virtualenv (the default behaviour) is fine. The development team only uses this option during our automated testing since our test runner machines only contain a single Python environment so using virtualenvs is redundant.

### Changes to the data models

When changes are made to the data models defined in `vast_pipeline/models.py`, the database schema needs to be updated to reflect those changes. Django can handle this for you by generating migration files that contain the necessary code to update the schema. Migration files are generated with the Django management command `python manage.py makemigrations` and applied to the database with `python manage.py migrate`. Depending on the nature of the changes, this may break backward compatibility, i.e. runs created with previous versions of the pipeline may not be compatible with your changes.

Database migrations must be committed to source control so that others can pull in your model changes. They can sometimes be complex and require additional attention. If you have any difficulty with migrations, please contact the VAST development team for help. More information can be found in the [Django documentation on migrations](https://docs.djangoproject.com/en/3.2/topics/migrations/).

### Removing/Clearing Data

The following sub-sections show how to completely drop every data in the database and how to remove only the data related to one or more pipeline runs.

#### Reset the database

Make sure you installed the [requirements `dev.txt`](https://github.com/apache/incubator-superset/blob/master/requirements/dev.txt){:target="_blank"}. And `django_extensions` is in `EXTRA_APPS` in your setting configuration file `.env` (e.g. `EXTRA_APPS=django_extensions,another_app,...`).

```bash
(pipeline_env)$ ./manage.py reset_db  && ./manage.py migrate
# use the following for no confirmation prompt
(pipeline_env)$ ./manage.py reset_db --noinput  && ./manage.py migrate
```

#### Clearing Run Data

It is sometimes convenient to remove the data belonging to one or more pipeline runs while developing the code base. This is particularly useful to save time by not having to re-upload the image data along with the measurements. The data related to the pipeline are the Sources, Associations, Forced extractions entries in database and the parquet files in the respective folder. By default the command will keep the run folder with the config and the log files.

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

## FrontEnd Assets Management and Guidelines

This guide explain the installation, compilation and development of the front end assets (HTML, CSS, JS and relative modules). We make use of a `node` installation with `npm` and `gulp` tasks to build the front end assets.

### Installation of node packages

After installing a `node` version and `npm`, install the node modules using from the base folder (`vast-pipeline`):

```bash
npm ci
```

`Npm` will install the node packages in a `node_modules` folder under the main root.

```bash
...
├── node_modules
...
```

For installing future additional dependencies you can run `npm install --save my-package` or `npm install --save-dev my-dev-package` (to save a development module), and after that commit __both__ `package.json` and `package-lock.json` files. For details about the installed packages and npm scripts see [`package.json`](https://github.com/apache/incubator-superset/blob/master/package.json){:target="_blank"}.

### FrontEnd Tasks with `gulp`

Using `gulp` and `npm` scripts you can:

1. Install dependencies under the `./static/vendor` folder.
2. Building (e.g. minify/uglify) CSS and/or Javascript files.
3. Run a development server that "hot-reload" your web page when any HTML, CSS or Javascript file is modified.

The command to list all the `gulp` "tasks" and sub-tasks is (you might need `gulp-cli` installed globally, i.e. `npm i --global gulp-cli`, more info [here](https://gulpjs.com/docs/en/getting-started/quick-start){:target="_blank"}):

```bash
gulp --tasks
```

Output:

```console
[11:55:30] Tasks for ~/PATH/TO/REPO/vast-pipeline/gulpfile.js
[11:55:30] ├── clean
[11:55:30] ├─┬ js9
[11:55:30] │ └─┬ <series>
[11:55:30] │   ├── js9Dir
[11:55:30] │   ├── js9MakeConfig
[11:55:30] │   ├── js9Make
[11:55:30] │   ├── js9MakeInst
[11:55:30] │   └── js9Config
[11:55:30] ├── css
[11:55:30] ├── js
[11:55:30] ├─┬ vendor
[11:55:30] │ └─┬ <parallel>
[11:55:30] │   ├── modules
[11:55:30] │   └─┬ <series>
[11:55:30] │     ├── js9Dir
[11:55:30] │     ├── js9MakeConfig
[11:55:30] │     ├── js9Make
[11:55:30] │     ├── js9MakeInst
[11:55:30] │     └── js9Config
[11:55:30] ├─┬ build
[11:55:30] │ └─┬ <series>
[11:55:30] │   ├─┬ <parallel>
[11:55:30] │   │ ├── modules
[11:55:30] │   │ └─┬ <series>
[11:55:30] │   │   ├── js9Dir
[11:55:30] │   │   ├── js9MakeConfig
[11:55:30] │   │   ├── js9Make
[11:55:30] │   │   ├── js9MakeInst
[11:55:30] │   │   └── js9Config
[11:55:30] │   └─┬ <parallel>
[11:55:30] │     ├── cssTask
[11:55:30] │     └── jsTask
[11:55:30] ├─┬ watch
[11:55:30] │ └─┬ <series>
[11:55:30] │   ├─┬ <parallel>
[11:55:30] │   │ ├── cssTask
[11:55:30] │   │ └── jsTask
[11:55:30] │   └─┬ <parallel>
[11:55:30] │     ├── watchFiles
[11:55:30] │     └── browserSync
[11:55:30] ├─┬ default
[11:55:30] │ └─┬ <series>
[11:55:30] │   ├─┬ <parallel>
[11:55:30] │   │ ├── modules
[11:55:30] │   │ └─┬ <series>
[11:55:30] │   │   ├── js9Dir
[11:55:30] │   │   ├── js9MakeConfig
[11:55:30] │   │   ├── js9Make
[11:55:30] │   │   ├── js9MakeInst
[11:55:30] │   │   └── js9Config
[11:55:30] │   └─┬ <parallel>
[11:55:30] │     ├── cssTask
[11:55:30] │     └── jsTask
[11:55:30] └── debug
```

Alternatively you can run gulp from the installed version in the `node_modules` folder with:

```bash
./node_modules/.bin/gulp --tasks
```

For further details about tasks, see [`gulpfile`](https://github.com/apache/incubator-superset/blob/master/gulpfile.js){:target="_blank"}.

#### 1. Install Dependencies under `vendor` Folder

Install the dependencies under the `./static/vendor` folder, with:

```bash
npm run vendor
```

Or, using global `gulp-cli`:

```bash
gulp vendor
```

As seen in the tasks diagram above, the `vendor` task run the module task in parallel with the js9 tasks. JS9 has many task as these run with manual command that involve `make/make install` and then writing configuration to `js9prefs.js` file. You can run manually the installation of JS9 with `gulp js9`.

#### 2. Building CSS and Javascript files

```bash
npm run build
# or
npm start
# or
gulp build
# or
gulp default
# or
gulp
```

will run the vendor task and minify both CSS and Javascript files. By default, when no other tasks is specified, `gulp` runs the build task. You can run single tasks with:

```bash
gulp css
```

to run just the minification of the CSS files.

#### 3. Run Development Server

Start your normal Django server with (__NOTE__: do not change the default port!):

```bash
(pipeline_env)$: ./manage.py runserver
```

In another terminal run:

```bash
npm run watch
# or
gulp watch
```

The latter will open your dev server, that will auto reload and apply your latest changes in any CSS, Javascript and/or HTML files. As pointed out in the gulp task tree above the `watch` task run both the vendor and build tasks.

#### 4. Debug Task

This task is for debugging the paths used in the others task, but also serve as a place holder to debug commands.

```bash
npm run debug
# or
gulp debug
```

#### 5. Clean Task

This task delete the vendor folder (`/static/vendor`) along with all the files.

```bash
npm run clean
# or
gulp clean
```

### FrontEnd assets for Production

In order to compile the frontend assets for production, activate the Python virtual environment, then run:

```bash
(pipeline_env)$ npm run js9staticprod && ./manage.py collectstatic -c
```

This command will collect all static assets (Javascript and CSS files) and copy them to `STATIC_ROOT` path in setting.py, so make sure you have permission to write to that. `STATIC_ROOT` is assigned to `./staticfiles` by default, otherwise assigned to the path you defined in your `.env` file.

The `js9staticprod` gulp task is necessary if you specify a `STATIC_URL` and a `BASE_URL` different than the default, for example if you need to prefix the site `/` with a base url because you are running another webserver (e.g. another web server is running on `https://my-astro-platform.com/` so you want to run the pipeline on the same server/domain `https://my-astro-platform.com/pipeline`, so you need to set `BASE_URL='/pipeline/'` and `STATIC_URL=/pipeline-static/` in `settings.py`). __We recommend to run this in any case!__

Then you can move that folder to where it can be served by the production static files server ([Ningx](https://www.nginx.com/){:target="_blank"} or [Apache](https://httpd.apache.org/){:target="_blank"} are usually good choices, in case refer to the [Django documentation](https://docs.djangoproject.com/en/3.1/howto/deployment/){:target="_blank"}).
