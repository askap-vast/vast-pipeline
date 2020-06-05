# FrontEnd Assets Management

This guide explain the installation and compilation of the front end assets (HTML, CSS, JS and relative modules). We make use of a `node` installation with `npm` and `gulp` tasks.

## Installation of node packages
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

For installing future additional dependecies you can run `npm install --save my-package` or `npm install --save-dev my-dev-package` (to save a development module), and after that commit __both__ `package.json` and `package-lock.json` files. For details about the installed packages and npm scripts see [`package.json`](./package.json).

## FrontEnd Tasks with `gulp`

Using `gulp` and `npm` scripts you can:

1. Install dependencies under the `./static/vendor` folder.
2. Building (e.g. minify/uglify) CSS and/or Javascript files.
3. Run a developement server that hot-reload your web page when any HTML, CSS or Javascript file is modified.

Listing `gulp` tasks and understanding sub-tasks within tasks, you might need `gulp-cli` installed globally (see `npm i --global gulp-cli`, more info [here](https://gulpjs.com/docs/en/getting-started/quick-start)), and then run:

```bash
gulp --tasks
```

Output:
```bash
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

For further details about tasks, see [`gulpfile`](./gulpfile.js).

### 1. Install Dependencies under `vendor` Folder
Install the dependencies under the `./static/vendor` folder, with:

```bash
npm run vendor
```
Or, using global `gulp-cli`:

```bash
gulp vendor
```

As seen in the tasks diagram above, the `vendor` task run the module task in parallel with the js9 tasks. JS9 has many task as these run with manual command that involve `make/make install` and then writing configuration to `js9prefs.js` file. You can run manually the installation of JS9 with `gulp js9`.

### 2. Building CSS and Javascript files

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

will run the vendor task and minify both CSS and Javascript files. Gulp default task is set up equal to build task. You can run single tasks with:

```bash
gulp css
```

to run just the minification of the CSS files.


### 3. Run Developement Server

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


### Debug Task
This task is for debugging the paths used in the others task, but also serve as a palce hodler to debug commands.

```bash
npm run debug
# or
gulp debug
```

### Clean Task
This task delete the vendor folder (`/static/vendor`) along with all the files.

```bash
npm run clean
# or
gulp clean
```
