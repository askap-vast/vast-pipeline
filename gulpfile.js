'use strict';

// Load plugins
const gulp = require("gulp"),
      browsersync = require("browser-sync").create(),
      cleanCSS = require("gulp-clean-css"),
      sourcemaps = require('gulp-sourcemaps'),
      del = require("del"),
      merge = require("merge-stream"),
      rename = require("gulp-rename"),
      uglify = require("gulp-uglify"),
      pkg = require('./package.json');


// Relative paths function
const pathsConfig = function () {
  let root = ".";
  let dist = root + '/static';
  let cssFolder = dist + '/css';
  let jsFolder = dist + '/js';

  return {
    root: root,
    templates: root + '/templates/**/*.html',
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
  return merge(bootstrapJS, chartJS, dataTables, fontAwesome, jquery, jqueryEasing, d3Celestial, d3CelestialData, d3CelestialImage);
}

// CSS task
function css() {
  return gulp
    .src([
      paths.css,
      '!./static/css/*.min.css',
    ])
    .pipe(sourcemaps.init())
    .pipe(rename({suffix: ".min"}))
    .pipe(cleanCSS())
    .pipe(sourcemaps.write())
    .pipe(gulp.dest(paths.cssDir))
    .pipe(browsersync.stream());
}

// JS task
function js() {
  return gulp
    .src([
      paths.js,
      '!./js/*.min.js',
    ])
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


// Define complex tasks
// const vendor = gulp.series(clean, modules);
const vendor = modules;
// const build = gulp.series(vendor, gulp.parallel(css, js));
const build = gulp.series(vendor, js);
// const watch = gulp.series(build, gulp.parallel(watchFiles, browserSync));

// Export tasks
exports.css = css;
exports.js = js;
// exports.clean = clean;
exports.vendor = vendor;
exports.build = build;
// exports.watch = watch;
exports.default = build;
exports.debug = debug;
