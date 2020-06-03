# FrontEnd Assets Management

This guide

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
[12:51:26] Tasks for ~/PATH/TO/REPO/vast-pipeline/gulpfile.js
[12:51:26] ├── css
[12:51:26] ├── js
[12:51:26] ├── vendor
[12:51:26] ├─┬ build
[12:51:26] │ └─┬ <series>
[12:51:26] │   ├── modules
[12:51:26] │   └─┬ <parallel>
[12:51:26] │     ├── cssTask
[12:51:26] │     └── jsTask
[12:51:26] ├─┬ watch
[12:51:26] │ └─┬ <series>
[12:51:26] │   ├─┬ <series>
[12:51:26] │   │ ├── modules
[12:51:26] │   │ └─┬ <parallel>
[12:51:26] │   │   ├── cssTask
[12:51:26] │   │   └── jsTask
[12:51:26] │   └─┬ <parallel>
[12:51:26] │     ├── watchFiles
[12:51:26] │     └── browserSync
[12:51:26] ├─┬ default
[12:51:26] │ └─┬ <series>
[12:51:26] │   ├── modules
[12:51:26] │   └─┬ <parallel>
[12:51:26] │     ├── cssTask
[12:51:26] │     └── jsTask
[12:51:26] └── debug
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
