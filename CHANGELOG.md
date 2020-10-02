# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with an added `List of PRs` section and links to the relevant PRs on the individal updates. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/askap-vast/vast-pipeline/compare/0.1.0...HEAD)

#### Added
- Added the ability for the pipeline to read in groups of images which are defined as a single `epoch` [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added the ability of the pipeline to remove duplicated measurements from an epoch [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added option to control separation measurements which are defined as a duplicate [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added the ability of the pipeline to separate images to associate into unique sky region groups [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added option to perform assocication of separate sky region groups in parallel [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added new options to webinterface pipeline run creation [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Added `epoch_based` column run model [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
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
- Rewritten relation functions to improve speed [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Minor changes to association to increase speed [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Changes to decrease memory usage during the calculation of the ideal coverage dataframe [#307](https://github.com/askap-vast/vast-pipeline/pull/307).
- Updated the `get_src_skyregion_merged_df` logic to account for epochs [#277](https://github.com/askap-vast/vast-pipeline/pull/277).
- Multiple changes to webinterface page layouts [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Changes source names to the format `ASKAP_hhmmss.ss(+/-)ddmmss.ss` [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Simplified webinterface navbar [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Excludes sources and pipeline runs from being listed in the source query page that are not complete on the webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Clarifies number of measurements on webinterface detail pages [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Changed `N.A.` labels to `N/A` on the webinterface [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Fixed 
- Fixes webinterface navbar overspill at small sizes [#345](https://github.com/askap-vast/vast-pipeline/pull/345).
- Fixes webinterface favourite source table [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### Removed
- Removed `static/css/collapse-box.css`, content moved to `pipeline.css` [#345](https://github.com/askap-vast/vast-pipeline/pull/345).

#### List of PRs
- [#307](https://github.com/askap-vast/vast-pipeline/pull/307) feat: Improve relation functions and general association speed ups.
- [#277](https://github.com/askap-vast/vast-pipeline/pull/277) feat,model: Parallel and epoch based association.
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
