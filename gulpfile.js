'use strict';

// resources to look
// https://cookiecutter-django-gulp.readthedocs.io/en/latest/gulp-tasks.html#gulp-tasks
// https://lincolnloop.com/blog/integrating-front-end-tools-your-django-project/
// https://blog.mozilla.org/webdev/2016/05/27/django-pipeline-and-gulp/
// https://gist.github.com/soin08/4793992d8cc537f62df3

// Load plugins
const gulp = require('gulp'),
      browsersync = require('browser-sync').create(),
      cleanCSS = require('gulp-clean-css'),
      sourcemaps = require('gulp-sourcemaps'),
      del = require('del'),
      merge = require('merge-stream'),
      rename = require('gulp-rename'),
      uglify = require('gulp-uglify'),
      babel = require('gulp-babel'),
      // exec = require('child_process').exec,
      // spawn = require('child_process').spawn,
      run = require('gulp-run-command').default,
      fs = require('fs'),
      pkg = require('./package.json');


// Relative paths function
const pathsConfig = function () {
  let root = __dirname;
  let dist = root + '/static';
  let cssFolder = dist + '/css';
  let jsFolder = dist + '/js';

  return {
    root: root,
    html: root + '/templates/**/*.html',
    cssDir: cssFolder,
    css: cssFolder + '/**/*.css',
    cssMin: cssFolder + '/**/*.min.css',
    jsDir: jsFolder,
    js: jsFolder + '/**/*.js',
    jsMin: jsFolder + '/**/*.min.js',
    dist: dist,
    vendor: dist + '/vendor',
    js9Target: dist + '/vendor/js9',
  }
};

const paths = pathsConfig();


// Debug task
function debug(cb) {
  console.log(paths)
  return cb();
}

// // Run django server
// function runServer() {
//   return exec('python manage.py runserver', function (err, stdout, stderr) {
//     console.log(stdout);
//     console.log(stderr);
//   });
// };

// JS9 tasks
function js9Dir() {
  var mkDir = run('mkdir -p ' + paths.js9Target)
  return mkDir();
}

function js9MakeConfig() {
  var config = run(
    './configure --with-webdir=' + paths.js9Target + ' --with-helper=nodejs',
    {cwd: './node_modules/js9'}
  )
  return config();
}

function js9Make() {
  var make = run('make', {cwd: './node_modules/js9'})
  return make();
}

function js9MakeInst() {
  var makeInst = run('make install', {cwd: './node_modules/js9'})
  return makeInst();
}

function js9Config(bc) {
  // read JSON config and append extra paramenters
  let js9Config = require(paths.js9Target + '/js9Prefs.json')
  js9Config.globalOpts.installDir = paths.js9Target.replace(paths.root, '')
  js9Config.globalOpts.syncOps = [
    "colormap",
    "contrastbias",
    "flip",
    "pan",
    "rot90",
    "scale",
    "wcs",
    "zoom"
  ]
  js9Config.textColorOpts = {"info": "#000064"}

  let outConfig = 'var JS9Prefs = ' + JSON.stringify(js9Config)
  // Write JS file with JSON config
  return fs.writeFile(paths.js9Target + '/js9prefs.js', outConfig, bc);
}

// BrowserSync
function browserSync(done) {
  browsersync.init(
    {
      port: 8001,
      proxy: "localhost:8000"
    }
  );
  done();
}

// BrowserSync reload
function browserSyncReload(done) {
  browsersync.reload();
  done();
}

// Clean vendor
function clean() {
  return del([paths.vendor]);
}

// Bring third party dependencies from node_modules into vendor directory
function modules() {
  // Bootstrap JS
  var bootstrapJS = gulp.src('./node_modules/bootstrap/dist/js/*')
    .pipe(gulp.dest(paths.vendor + '/bootstrap/js'));

  // ChartJS
  var chartJS = gulp.src([
      './node_modules/chart.js/dist/*.js',
      './node_modules/chartjs-plugin-error-bars/build/*.js'
    ])
    .pipe(gulp.dest(paths.vendor + '/chart.js'));

  // dataTables
  var dataTables = gulp.src([
      './node_modules/datatables.net/js/*.js',
      './node_modules/datatables.net-bs4/js/*.js',
      './node_modules/datatables.net-bs4/css/*.css'
    ])
    .pipe(gulp.dest(paths.vendor + '/datatables'));

  // Font Awesome
  var fontAwesome = gulp.src('./node_modules/@fortawesome/**/*')
    .pipe(gulp.dest(paths.vendor + ''));

  // jQuery Easing
  var jqueryEasing = gulp.src('./node_modules/jquery.easing/*.js')
    .pipe(gulp.dest(paths.vendor + '/jquery-easing'));

  // jQuery
  var jquery = gulp.src([
      './node_modules/jquery/dist/*',
      '!./node_modules/jquery/dist/core.js'
    ])
    .pipe(gulp.dest(paths.vendor + '/jquery'));

  // d3 celestial
  var d3Celestial = gulp.src([
      './node_modules/d3-celestial/celestial*.js',
      './node_modules/d3-celestial/lib/d3*.js'
    ])
    .pipe(gulp.dest(paths.vendor + '/d3-celestial'));
  var d3CelestialData = gulp.src('./node_modules/d3-celestial/data/*.json')
    .pipe(gulp.dest(paths.vendor + '/d3-celestial/data'));
  var d3CelestialImage = gulp.src('./node_modules/d3-celestial/images/*')
    .pipe(gulp.dest(paths.cssDir + '/images'));

  // particles.js
  var particlesJs = gulp.src('./node_modules/particles.js/particles.js')
    .pipe(gulp.dest(paths.vendor + '/particles.js'));

  return merge(bootstrapJS, chartJS, dataTables, fontAwesome, jquery, jqueryEasing, d3Celestial, d3CelestialData, d3CelestialImage, particlesJs);
}

// CSS task
function cssTask() {
  return gulp
    .src([
      paths.css,
      '!' + paths.cssMin,
    ])
    // .pipe(sourcemaps.init())
    .pipe(rename({
      suffix: '.min'
    }))
    .pipe(cleanCSS())
    // .pipe(sourcemaps.write())
    .pipe(gulp.dest(paths.cssDir))
    .pipe(browsersync.stream());
}

// JS task
function jsTask() {
  return gulp
    .src([
      paths.js,
      '!' + paths.jsMin,
    ])
    .pipe(babel({
      presets: ['@babel/env']
    }))
    .pipe(uglify())
    // .pipe(header(banner, {
    //   pkg: pkg
    // }))
    .pipe(rename({
      suffix: '.min'
    }))
    .pipe(gulp.dest(paths.jsDir))
    .pipe(browsersync.stream());
}

// Watch files
function watchFiles() {
  gulp.watch([paths.css, '!' + paths.cssMin], cssTask);
  gulp.watch([paths.js, '!' + paths.jsMin], jsTask);
  gulp.watch(paths.html, browserSyncReload);
}

// Define complex tasks
// const vendor = gulp.series(clean, modules);
// const build = gulp.series(vendor, gulp.parallel(css, js));
const js9 = gulp.series(js9Dir, js9MakeConfig, js9Make, js9MakeInst, js9Config)
const assets = gulp.parallel(cssTask, jsTask)
const vendor = gulp.parallel(modules, js9)
const build = gulp.series(vendor, assets);
const watch = gulp.series(assets, gulp.parallel(watchFiles, browserSync));

// Export tasks
exports.clean = clean;
exports.js9 = js9;
exports.css = cssTask;
exports.js = jsTask;
// exports.clean = clean;
exports.vendor = vendor;
exports.build = build;
exports.watch = watch;
exports.default = build;
exports.debug = debug;
