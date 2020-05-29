'use strict';

// Load plugins
const browsersync = require("browser-sync").create();
const cleanCSS = require("gulp-clean-css");
const del = require("del");
const gulp = require("gulp");
const merge = require("merge-stream");
const plumber = require("gulp-plumber");
const rename = require("gulp-rename");
const uglify = require("gulp-uglify");


// Load package.json for banner
const pkg = require('./package.json');

// // Run django server
// function runServer() {
//   return gulp.exec('python manage.py runserver', function (err, stdout, stderr) {
//     console.log(stdout);
//     console.log(stderr);
//   });
// };

// Clean vendor
function clean() {
  return del(["./vendor/"]);
}

// Bring third party dependencies from node_modules into vendor directory
function modules() {
  // Bootstrap JS
  var bootstrapJS = gulp.src('./node_modules/bootstrap/dist/js/*')
    .pipe(gulp.dest('./vendor/bootstrap/js'));
  // Bootstrap SCSS
  // var bootstrapSCSS = gulp.src('./node_modules/bootstrap/scss/**/*')
  //   .pipe(gulp.dest('./vendor/bootstrap/scss'));
  // ChartJS
  var chartJS = gulp.src('./node_modules/chart.js/dist/*.js')
    .pipe(gulp.dest('./vendor/chart.js'));
  // dataTables
  var dataTables = gulp.src([
      './node_modules/datatables.net/js/*.js',
      './node_modules/datatables.net-bs4/js/*.js',
      './node_modules/datatables.net-bs4/css/*.css'
    ])
    .pipe(gulp.dest('./vendor/datatables'));
  // Font Awesome
  var fontAwesome = gulp.src('./node_modules/@fortawesome/**/*')
    .pipe(gulp.dest('./vendor'));
  // jQuery Easing
  var jqueryEasing = gulp.src('./node_modules/jquery.easing/*.js')
    .pipe(gulp.dest('./vendor/jquery-easing'));
  // jQuery
  var jquery = gulp.src([
      './node_modules/jquery/dist/*',
      '!./node_modules/jquery/dist/core.js'
    ])
    .pipe(gulp.dest('./vendor/jquery'));
  // return merge(bootstrapJS, bootstrapSCSS, chartJS, dataTables, fontAwesome, jquery, jqueryEasing);
  return merge(bootstrapJS, chartJS, dataTables, fontAwesome, jquery, jqueryEasing);
}

// Define complex tasks
// const vendor = gulp.series(clean, modules);
const vendor = modules;
// const build = gulp.series(vendor, gulp.parallel(css, js));
// const watch = gulp.series(build, gulp.parallel(watchFiles, browserSync));

// Export tasks
// exports.css = css;
// exports.js = js;
// exports.clean = clean;
exports.vendor = vendor;
// exports.build = build;
// exports.watch = watch;
// exports.default = build;
