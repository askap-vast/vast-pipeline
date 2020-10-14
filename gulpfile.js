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
  sass = require("gulp-sass"),
  autoprefixer = require("gulp-autoprefixer"),
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
  let scssFolder = root + '/scss';
  let jsFolder = dist + '/js';

  return {
    root: root,
    html: root + '/templates/**/*.html',
    cssDir: cssFolder,
    css: cssFolder + '/**/*.css',
    cssMin: cssFolder + '/**/*.min.css',
    scssDir: scssFolder,
    scss: scssFolder + '/**/*.scss',
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
    './configure --with-webdir=' + paths.js9Target,
    { cwd: './node_modules/js9' }
  )
  return config();
}

function js9Make() {
  var make = run('make', { cwd: './node_modules/js9' })
  return make();
}

function js9MakeInst() {
  var makeInst = run('make install', { cwd: './node_modules/js9' })
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
  js9Config.textColorOpts = { "info": "#000064" }

  let outConfig = 'var JS9Prefs = ' + JSON.stringify(js9Config)
  // Write JS file with JSON config
  return fs.writeFile(paths.js9Target + '/js9prefs.js', outConfig, bc);
}

// JS9 CSS have some references to *.gif wrong and Django collectstatic
// command (with WhiteNoise installed) failed
// see issue https://github.com/ericmandel/js9/issues/74
function js9DelCSS() {
  return del([
    paths.js9Target + '/**/*.css',
    '!' + paths.js9Target + '/js9-allinone.css',
  ]);
}

function js9MoveGif() {
  return gulp
    .src([paths.js9Target + '/images/*.gif'])
    .pipe(gulp.dest(paths.js9Target));
}

function js9FixStaticUrl(bc) {
  const result = require('dotenv').config({ 'path': './webinterface/.env' })
  if (result.error) {
    throw result.error
  }
  let base_url = result.parsed.BASE_URL || null,
    static_url = result.parsed.STATIC_URL || '/static/',
    fileContent = fs.readFileSync(paths.js9Target + '/js9prefs.js', 'utf8')
  let serving_url = (base_url) ? '/' + base_url.split('/').join('') + '/' + static_url.split('/').join('') + '/' : static_url
  return fs.writeFile(
    paths.js9Target + '/js9prefs.js',
    fileContent.replace('/static/', serving_url),
    bc
  );
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

  // Bootstrap Select
  var bootstrapSelectJS = gulp.src('./node_modules/bootstrap-select/dist/js/*')
    .pipe(gulp.dest(paths.vendor + '/bootstrap-select/js'));
  var bootstrapSelectCSS = gulp.src('./node_modules/bootstrap-select/dist/css/*')
    .pipe(gulp.dest(paths.vendor + '/bootstrap-select/css'));

  // Bokeh
  var bokehJS = gulp.src('./node_modules/@bokeh/bokehjs/build/js/bokeh.min.js')
    .pipe(gulp.dest(paths.vendor + '/bokehjs'));

  // SB Admin 2 Bootstrap template
  var bootstrapSbAdmin2 = gulp.src([
    './node_modules/startbootstrap-sb-admin-2/js/*.js',
    './node_modules/startbootstrap-sb-admin-2/css/*.css'
  ]).pipe(gulp.dest(paths.vendor + '/startbootstrap-sb-admin-2'));

  // dataTables
  var dataTables = gulp.src([
    './node_modules/datatables.net/js/*.js',
    './node_modules/datatables.net-bs4/js/*.js',
    './node_modules/datatables.net-bs4/css/*.css'
  ])
    .pipe(gulp.dest(paths.vendor + '/datatables'));

  // dataTables-buttons
  var dataTablesButtons = gulp.src([
    './node_modules/datatables.net-buttons/js/*.js',
    './node_modules/datatables.net-buttons-bs4/js/*.js',
    './node_modules/datatables.net-buttons-bs4/css/*.css'
  ])
    .pipe(gulp.dest(paths.vendor + '/datatables-buttons'));

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

  // jszip
  var jszip = gulp.src([
    './node_modules/jszip/dist/*.js',
  ])
    .pipe(gulp.dest(paths.vendor + '/jszip'));

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

  // PrismJs
  var prismJs = gulp.src('./node_modules/prismjs/prism.js')
    .pipe(gulp.dest(paths.vendor + '/prismjs'));
  var prismJsPy = gulp.src('./node_modules/prismjs/components/prism-python.min.js')
    .pipe(gulp.dest(paths.vendor + '/prismjs'));
  var prismJsLineNum = gulp.src('./node_modules/prismjs/plugins/line-numbers/prism-line-numbers.min.js')
    .pipe(gulp.dest(paths.vendor + '/prismjs/line-numbers'));
  var prismJsCss = gulp.src('./node_modules/prismjs/themes/prism.css')
    .pipe(gulp.dest(paths.vendor + '/prismjs'));
  var prismJsLineNumCss = gulp.src('./node_modules/prismjs/plugins/line-numbers/prism-line-numbers.css')
    .pipe(gulp.dest(paths.vendor + '/prismjs/line-numbers'));

  return merge(bootstrapJS, bootstrapSbAdmin2, bokehJS, dataTables, dataTablesButtons, fontAwesome, jquery, jqueryEasing, jszip, d3Celestial, d3CelestialData, d3CelestialImage, particlesJs, prismJs, prismJsPy, prismJsLineNum, prismJsCss, prismJsLineNumCss);
}

// SCSS task
function scssTask() {
  return gulp
  .src(paths.scss)
  .pipe(sass({
    outputStyle: "expanded",
  }))
  .on("error", sass.logError)
  .pipe(autoprefixer({
    cascade: false
  }))
  .pipe(gulp.dest(paths.cssDir));
}

// CSS task
function cssTask() {
  return gulp
    .src([
      paths.css,
      '!' + paths.cssMin,
    ])
    .pipe(sourcemaps.init())
    .pipe(rename({
      suffix: '.min'
    }))
    .pipe(cleanCSS())
    .pipe(sourcemaps.write('map'))
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
    .pipe(sourcemaps.init())
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
    .pipe(sourcemaps.write('map'))
    .pipe(gulp.dest(paths.jsDir))
    .pipe(browsersync.stream());
}

// Watch files
function watchFiles() {
  gulp.watch(paths.scss, scssTask);
  gulp.watch([paths.css, '!' + paths.cssMin], cssTask);
  gulp.watch([paths.js, '!' + paths.jsMin], jsTask);
  gulp.watch(paths.html, browserSyncReload);
}

// Define complex tasks
const js9 = gulp.series(js9Dir, js9MakeConfig, js9Make, js9MakeInst, js9Config)
const assets = gulp.parallel(gulp.series(scssTask, cssTask), jsTask)
const vendor = gulp.series(clean, gulp.parallel(modules, js9))
const build = gulp.series(vendor, assets);
const watch = gulp.series(assets, gulp.parallel(watchFiles, browserSync));

// Export tasks
exports.clean = clean;
exports.js9 = js9;
exports.css = cssTask;
exports.js = jsTask;
exports.vendor = vendor;
exports.build = build;
exports.watch = watch;
exports.default = build;
exports.debug = debug;
exports.js9staticprod = gulp.parallel(js9DelCSS, js9MoveGif, js9FixStaticUrl);
