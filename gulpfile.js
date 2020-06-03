'use strict';

// resources to look
// https://cookiecutter-django-gulp.readthedocs.io/en/latest/gulp-tasks.html#gulp-tasks
// https://lincolnloop.com/blog/integrating-front-end-tools-your-django-project/
// https://blog.mozilla.org/webdev/2016/05/27/django-pipeline-and-gulp/
// https://gist.github.com/soin08/4793992d8cc537f62df3

// Load plugins
const gulp = require("gulp"),
      browsersync = require("browser-sync").create(),
      cleanCSS = require("gulp-clean-css"),
      sourcemaps = require('gulp-sourcemaps'),
      del = require("del"),
      merge = require("merge-stream"),
      rename = require("gulp-rename"),
      uglify = require("gulp-uglify"),
      babel = require("gulp-babel"),
      pkg = require('./package.json');


// Relative paths function
const pathsConfig = function () {
  let root = ".";
  let dist = root + '/static';
  let cssFolder = dist + '/css';
  let jsFolder = dist + '/js';

  return {
    root: root,
    html: root + '/templates/**/*.html',
    cssDir: cssFolder,
    css: cssFolder + '/**/*.css',
    jsDir: jsFolder,
    js: jsFolder + '/**/*.js',
    dist: dist,
    vendor: dist + '/vendor',
  }
};

const paths = pathsConfig();


// Debug task
function debug() {
    console.log(paths)
  return gulp.src('.')
}

// // Run django server
// function runServer() {
//   return gulp.exec('python manage.py runserver', function (err, stdout, stderr) {
//     console.log(stdout);
//     console.log(stderr);
//   });
// };

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

  // // js9
  // var js9 = gulp.src([
  //     './node_modules/js9/**/*',
  //     '!./node_modules/js9/analysis-plugins',
  //     '!./node_modules/js9/analysis-wrappers',
  //     '!./node_modules/js9/astroem',
  //     '!./node_modules/js9/casa',
  //     '!./node_modules/js9/closure-compiler',
  //     '!./node_modules/js9/closure-help',
  //     '!./node_modules/js9/js9Tests',
  //     '!./node_modules/js9/js9debugextras',
  //     '!./node_modules/js9/node_modules',
  //     '!./node_modules/js9/threeways',
  //     '!./node_modules/js9/util',
  //     './node_modules/js9/**/*.js',
  //     './node_modules/js9/**/*.css',
  //     './node_modules/js9/js9-allinone.css',
  //     './node_modules/js9/js9prefs.js',
  //     './node_modules/js9/js9support.min.js',
  //     './node_modules/js9/js9.min.js',
  //     './node_modules/js9/js9plugins.js',
  //     './node_modules/js9/astroemw.wasm',
  //   ])
  //   .pipe(gulp.dest(paths.vendor + '/js9'));

  return merge(bootstrapJS, chartJS, dataTables, fontAwesome, jquery, jqueryEasing, d3Celestial, d3CelestialData, d3CelestialImage);
}

// CSS task
function cssTask() {
  return gulp
    .src([
      paths.css,
      '!./static/css/*.min.css',
    ])
    // .pipe(sourcemaps.init())
    .pipe(rename({suffix: ".min"}))
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
      '!' + paths.dist +'/js/*.min.js',
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
  gulp.watch([paths.css, '!./static/css/*.min.css'], gulp.series(cssTask, browserSyncReload));
  // gulp.watch(["./js/**/*", "!./js/**/*.min.js"], js);
  gulp.watch(paths.html, browserSyncReload);
}

// Define complex tasks
// const vendor = gulp.series(clean, modules);
// const build = gulp.series(vendor, gulp.parallel(css, js));
const build = gulp.series(modules, cssTask);
const watch = gulp.series(build, gulp.parallel(watchFiles, browserSync));

// Export tasks
exports.css = cssTask;
exports.js = jsTask;
// exports.clean = clean;
exports.vendor = modules;
exports.build = build;
exports.watch = watch;
exports.default = build;
exports.debug = debug;
