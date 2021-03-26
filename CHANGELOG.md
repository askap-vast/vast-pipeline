# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with an added `List of PRs` section and links to the relevant PRs on the individal updates. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/askap-vast/vast-pipeline/compare/0.2.0...HEAD)

#### Added

- Added script to auto-generate code reference documentation pages [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Added code reference section to documentation [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Added new pages and sections to documentation [#471](https://github.com/askap-vast/vast-pipeline/pull/471)
- Added image add mode run restore command 'restorepiperun' [#463](https://github.com/askap-vast/vast-pipeline/pull/463)
- Added documentation folder and files for `mkdocs` and CI [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Added add image to existing run feature [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Added networkx to base reqiurements [#460](https://github.com/askap-vast/vast-pipeline/pull/460).
- Added CI/CD workflow to run tests on pull requests [#446](https://github.com/askap-vast/vast-pipeline/pull/446)
- Added basic regression tests [#425](https://github.com/askap-vast/vast-pipeline/pull/425)
- Added image length validation for config [#425](https://github.com/askap-vast/vast-pipeline/pull/425)

#### Changed

- Changed non-google format docstrings to google format [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Changed some documentation layout and updated content [#471](https://github.com/askap-vast/vast-pipeline/pull/471).
- Changed 'cmd' flag in run pipeline to 'cli' [#466](https://github.com/askap-vast/vast-pipeline/pull/466).
- Changed `CONTRIBUTING.md` and `README.md` [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Changed forced extraction name suffix to run id rather than datetime [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Changed tests to run on smaller cutouts [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Changed particles style on login page [#459](https://github.com/askap-vast/vast-pipeline/pull/459).
- Dependabot: Bump ini from 1.3.5 to 1.3.8 [#436](https://github.com/askap-vast/vast-pipeline/pull/436)


#### Fixed

- Fixed Selavy catalogue ingest to discard the unit row before reading the data [#473](https://github.com/askap-vast/vast-pipeline/pull/473).
- Fixed initial job processing from the UI [#466](https://github.com/askap-vast/vast-pipeline/pull/466).
- Fixed links in `README.md` [#464](https://github.com/askap-vast/vast-pipeline/pull/464).
- Fixed basic association new sources created through relations [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Fixed tests running pipeline multiple times [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Fixed particles canvas sizing on login page [#459](https://github.com/askap-vast/vast-pipeline/pull/459).
- Fixed breadcrumb new line on small resolutitons [#459](https://github.com/askap-vast/vast-pipeline/pull/459).
- Fixed config files in tests [#430](https://github.com/askap-vast/vast-pipeline/pull/430)
- Fixed sources table on measurement detail page [#429](https://github.com/askap-vast/vast-pipeline/pull/429).
- Fixed missing meta columns in parallel association [#427](https://github.com/askap-vast/vast-pipeline/pull/427).

#### Removed

- Removed `INSTALL.md`, `PROFILE.md` and `static/README.md` [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Removed aplpy from base requirements [#460](https://github.com/askap-vast/vast-pipeline/pull/460).

#### List of PRs

- [#471](https://github.com/askap-vast/vast-pipeline/pull/471) feat: Documentation update.
- [#473](https://github.com/askap-vast/vast-pipeline/pull/473) fix: discard the selavy unit row before reading.
- [#466](https://github.com/askap-vast/vast-pipeline/pull/466) fix: Fixed initial job processing from the UI.
- [#463](https://github.com/askap-vast/vast-pipeline/pull/463) feat: Added image add mode run restore command.
- [#433](https://github.com/askap-vast/vast-pipeline/pull/433) doc: add documentation GitHub pages website with CI.
- [#443](https://github.com/askap-vast/vast-pipeline/pull/443) feat, fix: Adds the ability to add images to an existing run.
- [#460](https://github.com/askap-vast/vast-pipeline/pull/460) dep: Removed aplpy from base requirements.
- [#446](https://github.com/askap-vast/vast-pipeline/pull/446) feat: CI/CD workflow.
- [#459](https://github.com/askap-vast/vast-pipeline/pull/459) fix: Fix particles and breadcrumb issues on mobile.
- [#436](https://github.com/askap-vast/vast-pipeline/pull/436) dep: Bump ini from 1.3.5 to 1.3.8.
- [#430](https://github.com/askap-vast/vast-pipeline/pull/430) fix: Test config files.
- [#425](https://github.com/askap-vast/vast-pipeline/pull/425) feat: Basic regression tests.
- [#429](https://github.com/askap-vast/vast-pipeline/pull/429) fix: Fixed sources table on measurement detail page.
- [#427](https://github.com/askap-vast/vast-pipeline/pull/427) fix: Fixed missing meta columns in parallel association.

## [0.2.0](https://github.com/askap-vast/vast-pipeline/releases/0.2.0) (2020-11-30)

#### Added

- Added a check in the UI running that the job is not already running or queued [#421](https://github.com/askap-vast/vast-pipeline/pull/421).
- Added the deletion of all parquet and arrow files upon a re-run [#421](https://github.com/askap-vast/vast-pipeline/pull/421).
- Added source selection by name or ID on source query page [#401](https://github.com/askap-vast/vast-pipeline/pull/401).
- Added test cases [#412](https://github.com/askap-vast/vast-pipeline/pull/412)
- Added [askap-vast/forced_phot](https://github.com/askap-vast/forced_phot) to pip requirements [#408](https://github.com/askap-vast/vast-pipeline/pull/408).
- Added pipeline configuration parameter, `SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS`, to filter measurement pairs before calculating aggregate metrics [#407](https://github.com/askap-vast/vast-pipeline/pull/407).
- Added custom 404.html and 500.html templates for error pages [#415](https://github.com/askap-vast/vast-pipeline/pull/415)
- Added ability to export measurement_pairs.parqyet as an arrow file [#393](https://github.com/askap-vast/vast-pipeline/pull/393).
- Added new fields to detail pages and source and measurement tables [#406](https://github.com/askap-vast/vast-pipeline/pull/406).
- Added new fields to source query page (island flux ratio, min and max fluxes) [#406](https://github.com/askap-vast/vast-pipeline/pull/406).
- Added min, max flux values to sources and agg min island flux ratio field [#406](https://github.com/askap-vast/vast-pipeline/pull/406).
- Added island flux ratio column to measurements, component flux divided by total island flux (peak and int) [#406](https://github.com/askap-vast/vast-pipeline/pull/406).
- Added a maximum number of images for runs through the UI [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Added the ability to run a pipeline run through the UI [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Added `Queued` status to the list of pipeline run statuses [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Added the dependancy `django-q` that enables scheduled tasks to be processed [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Added source tagging [#396](https://github.com/askap-vast/vast-pipeline/pull/396).
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

- Renamed 'alert-wrapper' container to 'toast-wrapper' [#419](https://github.com/askap-vast/vast-pipeline/pull/419).
- Changed alerts to use the Bootstrap toasts system [#419](https://github.com/askap-vast/vast-pipeline/pull/419).
- Bumped some npm package versions to address dependabot security alerts [#411](https://github.com/askap-vast/vast-pipeline/pull/411).
- Images table on pipeline run detail page changed to order by datetime by default [#417](https://github.com/askap-vast/vast-pipeline/pull/417).
- Changed config argument `CREATE_MEASUREMENTS_ARROW_FILE` -> `CREATE_MEASUREMENTS_ARROW_FILES` [#393](https://github.com/askap-vast/vast-pipeline/pull/393).
- Naming of average flux query fields to account for other min max flux fields [#406](https://github.com/askap-vast/vast-pipeline/pull/406).
- Expanded `README.md` to include `DjangoQ` and UI job scheduling information [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Shifted alerts location to the top right [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Log file card now expanded by default on pipeline run detail page [#404](https://github.com/askap-vast/vast-pipeline/pull/404).
- Changed user comments on source detail pages to incorporate tagging feature [#396](https://github.com/askap-vast/vast-pipeline/pull/396).
- Updated RACS HiPS URL in Aladin [#399](https://github.com/askap-vast/vast-pipeline/pull/399).
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

- Fixed pipeline run DB loading in command line runpipeline command [#401](https://github.com/askap-vast/vast-pipeline/pull/401).
- Fixed nodejs version [#412](https://github.com/askap-vast/vast-pipeline/pull/412)
- Fixed npm start failure [#412](https://github.com/askap-vast/vast-pipeline/pull/412)
- All queries using the 2-epoch metric `Vs` now operate on `abs(Vs)`. The original `Vs` stored in MeasurementPair objects is still signed [#407](https://github.com/askap-vast/vast-pipeline/pull/407).
- Changed aggregate 2-epoch metric calculation for Source objects to ensure they come from the same pair [#407](https://github.com/askap-vast/vast-pipeline/pull/407).
- Fixed new sources rms measurement returns when no measurements are valid [#417](https://github.com/askap-vast/vast-pipeline/pull/417).
- Fixed measuring rms values from selavy created NAXIS=3 FITS images [#417](https://github.com/askap-vast/vast-pipeline/pull/417).
- Fixed rms value calculation in non-cluster forced extractions [#402](https://github.com/askap-vast/vast-pipeline/pull/402).
- Increase request limit for gunicorn [#398](https://github.com/askap-vast/vast-pipeline/pull/398).
- Fixed max source Vs metric to being an absolute value [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Fixed misalignment of lightcurve card header text and the flux type radio buttons [#386](https://github.com/askap-vast/vast-pipeline/pull/386).
- Fixes incorrently named GitHub `social-auth` settings variable that prevented users from logging in with GitHub [#372](https://github.com/askap-vast/vast-pipeline/pull/372).
- Fixes webinterface navbar overspill at small sizes [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Fixes webinterface favourite source table [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Removed

- Removed/Disabled obsolete test cases[#412](https://github.com/askap-vast/vast-pipeline/pull/412)
- Removed `vast_pipeline/pipeline/forced_phot.py` [#408](https://github.com/askap-vast/vast-pipeline/pull/408).
- Removed 'selavy' from homepage measurements count label [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Removed leftover `pipeline/plots.py` file [#391](https://github.com/askap-vast/vast-pipeline/pull/391).
- Removed `static/css/pipeline.css`, this file is now produced by compiling the Sass (`scss/**/*.scss`) files with Gulp [#370](https://github.com/askap-vast/vast-pipeline/pull/370).
- Removed any storage of `meas_dj_obj` or `src_dj_obj` in the pipeline [#382](https://github.com/askap-vast/vast-pipeline/pull/382).
- Removed `static/vendor/chart-js` package [#305](https://github.com/askap-vast/vast-pipeline/pull/305).
- Removed `static/css/collapse-box.css`, content moved to `pipeline.css` [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### List of PRs

- [#421](https://github.com/askap-vast/vast-pipeline/pull/421) feat: Delete output files on re-run & UI run check.
- [#401](https://github.com/askap-vast/vast-pipeline/pull/401) feat: Added source selection by name or id to query page.
- [#412](https://github.com/askap-vast/vast-pipeline/pull/412) feat: added some unit tests.
- [#419](https://github.com/askap-vast/vast-pipeline/pull/419) feat: Update alerts to use toasts.
- [#408](https://github.com/askap-vast/vast-pipeline/pull/408) feat: use forced_phot dependency instead of copied code.
- [#407](https://github.com/askap-vast/vast-pipeline/pull/407) fix, model: modified 2-epoch metric calculation.
- [#411](https://github.com/askap-vast/vast-pipeline/pull/411) fix: updated npm deps to fix security vulnerabilities.
- [#415](https://github.com/askap-vast/vast-pipeline/pull/415) feat: Added custom 404 and 500 templates.
- [#393](https://github.com/askap-vast/vast-pipeline/pull/393) feat: Added measurement_pairs arrow export.
- [#406](https://github.com/askap-vast/vast-pipeline/pull/406) feat, model: Added island flux ratio columns.
- [#402](https://github.com/askap-vast/vast-pipeline/pull/402) fix: Fixed rms value calculation in non-cluster forced extractions.
- [#404](https://github.com/askap-vast/vast-pipeline/pull/404) feat, dep, model: Completed schedule pipe run.
- [#396](https://github.com/askap-vast/vast-pipeline/pull/396) feat: added source tagging.
- [#398](https://github.com/askap-vast/vast-pipeline/pull/398) fix: gunicorn request limit
- [#399](https://github.com/askap-vast/vast-pipeline/pull/399) fix: Updated RACS HiPS path.
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

## [0.1.0](https://github.com/askap-vast/vast-pipeline/releases/0.1.0) (2020-09-27)

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
