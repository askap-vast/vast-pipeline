# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with an added `List of PRs` section and links to the relevant PRs on the individal updates. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/askap-vast/vast-pipeline/compare/0.1.0...HEAD)

#### Added

- Added link to measurement table from the lightcurve to source detail page [#387](https://github.com/askap-vast/vast-pipeline/pull/387).
- Added 'epoch based' parameter to pipeline run detail page [#387](https://github.com/askap-vast/vast-pipeline/pull/387).
- Adds basic commenting functionality for sources, measurements, images, and runs [#368](https://github.com/askap-vast/vast-pipeline/pull/368).
- Custom CSS now processed with Sass: Bootstrap and sb-admin-2 theme are compiled into a single stylesheet [#370](https://github.com/askap-vast/vast-pipeline/pull/370).
- Added `vast_pipeline/pipeline/generators.py` which contains generator functions [#382](https://github.com/askap-vast/vast-pipeline/pull/382).
- Range and NaN check on new source analysis to match forced extraction [#374](https://github.com/askap-vast/vast-pipeline/pull/374).
- Added the ability for the pipeline to read in groups of images which are defined as a single `epoch` [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added the ability of the pipeline to remove duplicated measurements from an epoch [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added option to control separation measurements which are defined as a duplicate [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added the ability of the pipeline to separate images to associate into unique sky region groups [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added option to perform assocication of separate sky region groups in parallel [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added new options to webinterface pipeline run creation [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added `epoch_based` column run model [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added links to tables and postage stamps on source detail page [#379](https://github.com/askap-vast/vast-pipeline/pull/379).
- Updates image `background_path` from current run when not originally provided [#377](https://github.com/askap-vast/vast-pipeline/pull/377).
- Added csv export button to datatables on webinterface [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Added support for Excel export button to datatables on webinterface (waiting on datatables buttons fix) [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Added column visibility button to datatables on webinterface [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Added dependancy datatables-buttons 1.6.4 [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Added dependancy jszip (required for Excel export) [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Adds `n_selavy_measurements` and `n_forced_measurements` to run model [#362](https://github.com/askap-vast/vast-pipeline/pull/362).
- Adds steps to populate new measurement count fields in pipeline run [#362](https://github.com/askap-vast/vast-pipeline/pull/362).
- Source order from the query is preserved on source detail view [#364](https://github.com/askap-vast/vast-pipeline/pull/364).
- Setting `HOME_DATA_DIR` to specify a directory relative to the user's home directory to scan for FITS and text files to use in a Run initialised with the UI [#361](https://github.com/askap-vast/vast-pipeline/pull/361).
- Adds a node graph to accompany the lightcurve that shows which measurement pairs exceed the default variability metric thresholds (`Vs >= 4.3`, `|m| >= 0.26`) [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Adds the `MeasurementPair` model to store two variability metrics for each flux type: Vs, the t-statistic; and m, the modulation index. The maximum of these metrics are also added to the `Source` model for joinless queries. These metrics are calculated during the pipeline run [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Adds radio buttons to change the lightcurve data points between peak and integrated fluxes [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Fills out information on all webinterface detail pages [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Adds frequency information the measurements and images webinterface tables. [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Adds celestial plot and tables to webinterface pipeline detail page [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Adds useful links to webinterface navbar [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Adds tool tips to webinterface source query [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Adds hash reading to webinterface source query to allow filling from URL hash parameters [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Add links to number cards on webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Added home icon on hover on webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Added copy-to-clipboard functionality on coordinates on webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Changed

- Changed home page changelog space to welcome/help messages [#387](https://github.com/askap-vast/vast-pipeline/pull/387).
- The `comment` field in the Run model has been renamed to `description`. A `comment` many-to-many relationship was added to permit user comments on Run instances [#368](https://github.com/askap-vast/vast-pipeline/pull/368).
- Moved sb-admin-2 Bootstrap theme static assets to NPM package dependency [#370](https://github.com/askap-vast/vast-pipeline/pull/370).
- Refactored bulk uploading to use iterable generator objects [#382](https://github.com/askap-vast/vast-pipeline/pull/382).
- Updated validation of config file to check that all options are present and valid [#373](https://github.com/askap-vast/vast-pipeline/pull/373).
- Rewritten relation functions to improve speed [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Minor changes to association to increase speed [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Changes to decrease memory usage during the calculation of the ideal coverage dataframe [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Updated the `get_src_skyregion_merged_df` logic to account for epochs [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Updated the job creation modal layout [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Bumped datatables-buttons to 1.6.5 and enabled excel export buttton [#380](https://github.com/askap-vast/vast-pipeline/pull/380).
- Bumped datatables to 1.10.22 [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Changed `dom` layout on datatables [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Changed external results table pagination buttons on source detail webinterface page pagination to include less numbers to avoid overlap [#363](https://github.com/askap-vast/vast-pipeline/pull/363).
- Changes measurement counts view on website to use new model parameters [#362](https://github.com/askap-vast/vast-pipeline/pull/362).
- Lightcurve plot now generated using Bokeh [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Multiple changes to webinterface page layouts [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Changes source names to the format `ASKAP_hhmmss.ss(+/-)ddmmss.ss` [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Simplified webinterface navbar [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Excludes sources and pipeline runs from being listed in the source query page that are not complete on the webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Clarifies number of measurements on webinterface detail pages [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Changed `N.A.` labels to `N/A` on the webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Fixed

- Fixed max source Vs metric to being an absolute value [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Fixed misalignment of lightcurve card header text and the flux type radio buttons [#386](https://github.com/askap-vast/vast-pipeline/pull/386).
- Fixes incorrently named GitHub `social-auth` settings variable that prevented users from logging in with GitHub [#372](https://github.com/askap-vast/vast-pipeline/pull/372).
- Fixes webinterface navbar overspill at small sizes [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Fixes webinterface favourite source table [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Removed

- Removed 'selavy' from homepage measurements count label [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Removed leftover `pipeline/plots.py` file [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Removed `static/css/pipeline.css`, this file is now produced by compiling the Sass (`scss/**/*.scss`) files with Gulp [#370](https://github.com/askap-vast/vast-pipeline/pull/370).
- Removed any storage of `meas_dj_obj` or `src_dj_obj` in the pipeline [#382](https://github.com/askap-vast/vast-pipeline/pull/382).
- Removed `static/vendor/chart-js` package [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Removed `static/css/collapse-box.css`, content moved to `pipeline.css` [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### List of PRs

- [#391](https://github.com/askap-vast/vast-pipeline/pull/391) fix: Vs metric fix and removed pipeline/plots.py.
- [#387](https://github.com/askap-vast/vast-pipeline/pull/387) feat: Minor website updates.
- [#386](https://github.com/askap-vast/vast-pipeline/pull/386) fix: fix lightcurve header floats.
- [#368](https://github.com/askap-vast/vast-pipeline/pull/368) feat: vast-candidates merger: Add user commenting
- [#370](https://github.com/askap-vast/vast-pipeline/pull/370) feat: moved sb-admin-2 assets to dependencies.
- [#382](https://github.com/askap-vast/vast-pipeline/pull/380) feat: Refactored bulk uploading of objects.
- [#374](https://github.com/askap-vast/vast-pipeline/pull/374) feat, fix: Bring new source checks inline with forced extraction.
- [#373](https://github.com/askap-vast/vast-pipeline/pull/373) fix: Check all options are valid and present in validate_cfg.
- [#307](https://github.com/askap-vast/vast-pipeline/pull/307) feat: Improve relation functions and general association speed ups.
- [#277](https://github.com/askap-vast/vast-pipeline/pull/277) feat,model: Parallel and epoch based association.
- [#380](https://github.com/askap-vast/vast-pipeline/pull/380) feat, dep: Enable Excel export button.
- [#379](https://github.com/askap-vast/vast-pipeline/pull/372) feat: Add links to source detail template.
- [#377](https://github.com/askap-vast/vast-pipeline/pull/377) fix: Update image bkg path when not originally provided.
- [#363](https://github.com/askap-vast/vast-pipeline/pull/363) feat, dep: Add export and column visibility buttons to tables.
- [#362](https://github.com/askap-vast/vast-pipeline/pull/362) feat, model: Added number of measurements to Run DB model.
- [#364](https://github.com/askap-vast/vast-pipeline/pull/361) feat: preserve source query order on detail view.
- [#361](https://github.com/askap-vast/vast-pipeline/pull/361) feat, fix: restrict home dir scan to specified directory.
- [#372](https://github.com/askap-vast/vast-pipeline/pull/372) fix: fix social auth scope setting name.
- [#305](https://github.com/askap-vast/vast-pipeline/pull/305) feat: 2 epoch metrics
- [#345](https://github.com/askap-vast/vast-pipeline/pull/345) feat, fix: Website improvements.

## [0.1.0](https://github.com/askap-vast/vast-pipeline/releases/0.1.0) (2020/09/27)

First release of the Vast Pipeline. This was able to process 707 images (EPOCH01 to EPOCH11x) on a machine with 64 GB of RAM.

#### List of PRs

- [#347](https://github.com/askap-vast/vast-pipeline/pull/347) feat: Towards first release
- [#354](https://github.com/askap-vast/vast-pipeline/pull/354) fix, model: Updated Band model fields to floats
- [#346](https://github.com/askap-vast/vast-pipeline/pull/346) fix: fix JS9 overflow in measurement detail view
- [#349](https://github.com/askap-vast/vast-pipeline/pull/349) dep: Bump lodash from 4.17.15 to 4.17.20
- [#348](https://github.com/askap-vast/vast-pipeline/pull/348) dep: Bump django from 3.0.5 to 3.0.7 in /requirements
- [#344](https://github.com/askap-vast/vast-pipeline/pull/344) fix: fixed aladin init for all pages
- [#340](https://github.com/askap-vast/vast-pipeline/pull/340) break: rename pipeline folder to vast_pipeline
- [#342](https://github.com/askap-vast/vast-pipeline/pull/342) fix: Hotfix - fixed parquet path on job detail view
- [#336](https://github.com/askap-vast/vast-pipeline/pull/336) feat: Simbad/NED async cone search
- [#284](https://github.com/askap-vast/vast-pipeline/pull/284) fix: Update Aladin surveys with RACS and VAST
- [#333](https://github.com/askap-vast/vast-pipeline/pull/333) feat: auth to GitHub org, add logging and docstring
- [#325](https://github.com/askap-vast/vast-pipeline/pull/325) fix, feat: fix forced extraction using Dask bags backend
- [#334](https://github.com/askap-vast/vast-pipeline/pull/334) doc: better migration management explanation
- [#332](https://github.com/askap-vast/vast-pipeline/pull/332) fix: added clean to build task, removed commented lines
- [#322](https://github.com/askap-vast/vast-pipeline/pull/322) fix, model: add unique to image name, remove timestamp from image folder
- [#321](https://github.com/askap-vast/vast-pipeline/pull/321) feat: added css and js sourcemaps
- [#314](https://github.com/askap-vast/vast-pipeline/pull/314) feat: query form redesign, sesame resolver, coord validator
- [#318](https://github.com/askap-vast/vast-pipeline/pull/318) feat: Suppress astropy warnings
- [#317](https://github.com/askap-vast/vast-pipeline/pull/317) fix: Forced photometry fixes for #298 and #312
- [#316](https://github.com/askap-vast/vast-pipeline/pull/316) fix: fix migration file 0001_initial.py
- [#310](https://github.com/askap-vast/vast-pipeline/pull/310) fix: Fix run detail number of measurements display
- [#309](https://github.com/askap-vast/vast-pipeline/pull/309) fix: Added JS9 overlay filters and changed JS9 overlay behaviour on sources and measurements
- [#303](https://github.com/askap-vast/vast-pipeline/pull/303) fix: Fix write config feedback and validation
- [#306](https://github.com/askap-vast/vast-pipeline/pull/306) feat: Add config validation checks
- [#302](https://github.com/askap-vast/vast-pipeline/pull/302) fix: Fix RA correction for d3 celestial
- [#300](https://github.com/askap-vast/vast-pipeline/pull/300) fix: increase line limit for gunicorn server
- [#299](https://github.com/askap-vast/vast-pipeline/pull/299) fix: fix admin "view site" redirect
- [#294](https://github.com/askap-vast/vast-pipeline/pull/294) fix: Make lightcurves start at zero
- [#268](https://github.com/askap-vast/vast-pipeline/pull/268) feat: Production set up with static files and command
- [#291](https://github.com/askap-vast/vast-pipeline/pull/291) fix: Bug fix for forced_photom cluster allow_nan
- [#289](https://github.com/askap-vast/vast-pipeline/pull/289) fix: Fix broken UI run creation
- [#287](https://github.com/askap-vast/vast-pipeline/pull/287) fix: Fix forced measurement parquet files write
- [#286](https://github.com/askap-vast/vast-pipeline/pull/286) fix: compile JS9 without helper option
- [#285](https://github.com/askap-vast/vast-pipeline/pull/285) fix: Fix removing forced parquet and clear images from piperun
