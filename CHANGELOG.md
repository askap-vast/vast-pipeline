<!--
follow https://github.com/apache/incubator-superset/blob/master/CHANGELOG.md
-->
## Change Log

### 0.1.0 (2020/09/27)

First release of the Vast Pipeline. This was able to process 707 images (EPOCH01 to EPOCH11x) on a machine with 64 GB of RAM.

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
- [#286](https://github.com/askap-vast/vast-pipeline/pull/285) fix: compile JS9 without helper option
- [#285](https://github.com/askap-vast/vast-pipeline/pull/285) fix: Fix removing forced parquet and clear images from piperun
