Change Log
==========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, with an added ``List of PRs`` section and links to the relevant PRs on the individal updates. This project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

`Unreleased <https://github.com/askap-vast/vast-pipeline/compare/0.1.0...HEAD>`_
--------------------------------------------------------------------------------

Added
+++++

* Added links to tables and postage stamps on source detail page `#379 <https://github.com/askap-vast/vast-pipeline/pull/379>`_
* Updates image ``background_path`` from current run when not originally provided `#377 <https://github.com/askap-vast/vast-pipeline/pull/377>`_
* Added csv export button to datatables on webinterface `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Added support for Excel export button to datatables on webinterface (waiting on datatables buttons fix) `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Added column visibility button to datatables on webinterface `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Added dependancy datatables-buttons 1.6.4 `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Added dependancy jszip (required for Excel export) `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Adds ``n_selavy_measurements`` and ``n_forced_measurements`` to run model `#362 <https://github.com/askap-vast/vast-pipeline/pull/362>`_
* Adds steps to populate new measurement count fields in pipeline run `#362 <https://github.com/askap-vast/vast-pipeline/pull/362>`_
* Source order from the query is preserved on source detail view `#364 <https://github.com/askap-vast/vast-pipeline/pull/364>`_
* Setting ``HOME_DATA_DIR`` to specify a directory relative to the user's home directory to scan for FITS and text files to use in a Run initialised with the UI `#361 <https://github.com/askap-vast/vast-pipeline/pull/361>`_
* Fills out information on all webinterface detail pages `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Adds frequency information the measurements and images webinterface tables. `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Adds celestial plot and tables to webinterface pipeline detail page `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Adds useful links to webinterface navbar `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Adds tool tips to webinterface source query `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Adds hash reading to webinterface source query to allow filling from URL hash parameters `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Add links to number cards on webinterface `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Added home icon on hover on webinterface `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Added copy-to-clipboard functionality on coordinates on webinterface `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_

Changed
+++++++

* Bumped datatables-buttons to 1.6.5 and enabled excel export buttton `#380 <https://github.com/askap-vast/vast-pipeline/pull/380>`_
* Bumped datatables to 1.10.22 `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Changed ``dom`` layout on datatables `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Changed external results table pagination buttons on source detail webinterface page pagination to include less numbers to avoid overlap `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_
* Changes measurement counts view on website to use new model parameters `#362 <https://github.com/askap-vast/vast-pipeline/pull/362>`_
* Multiple changes to webinterface page layouts `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Changes source names to the format ``ASKAP_hhmmss.ss(+/-)ddmmss.ss`` `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Simplified webinterface navbar `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Excludes sources and pipeline runs from being listed in the source query page that are not complete on the webinterface `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Clarifies number of measurements on webinterface detail pages `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Changed ``N.A.`` labels to ``N/A`` on the webinterface `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_

Fixed
+++++

* Fixes incorrently named GitHub ``social-auth`` settings variable that prevented users from logging in with GitHub `#372 <https://github.com/askap-vast/vast-pipeline/pull/372>`_
* Fixes webinterface navbar overspill at small sizes `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_
* Fixes webinterface favourite source table `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_

Removed
+++++++

* Removed ``static/css/collapse-box.css``, content moved to ``pipeline.css`` `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_

List of PRs
+++++++++++

* `#380 <https://github.com/askap-vast/vast-pipeline/pull/380>`_ feat, dep: Enable Excel export button.
* `#379 <https://github.com/askap-vast/vast-pipeline/pull/372>`_ feat: Add links to source detail template.
* `#377 <https://github.com/askap-vast/vast-pipeline/pull/377>`_ fix: Update image bkg path when not originally provided.
* `#363 <https://github.com/askap-vast/vast-pipeline/pull/363>`_ feat, dep: Add export and column visibility buttons to tables.
* `#362 <https://github.com/askap-vast/vast-pipeline/pull/362>`_ feat, model: Added number of measurements to Run DB model.
* `#364 <https://github.com/askap-vast/vast-pipeline/pull/361>`_ feat: preserve source query order on detail view.
* `#361 <https://github.com/askap-vast/vast-pipeline/pull/361>`_ feat, fix: restrict home dir scan to specified directory.
* `#372 <https://github.com/askap-vast/vast-pipeline/pull/372>`_ fix: fix social auth scope setting name.
* `#345 <https://github.com/askap-vast/vast-pipeline/pull/345>`_ feat, fix: Website improvements.

`0.1.0 <https://github.com/askap-vast/vast-pipeline/releases/0.1.0>`_ (2020/09/27)
----------------------------------------------------------------------------------

First release of the Vast Pipeline. This was able to process 707 images (EPOCH01 to EPOCH11x) on a machine with 64 GB of RAM.

List of PRs
+++++++++++

* `#347 <https://github.com/askap-vast/vast-pipeline/pull/347>`_ feat: Towards first release
* `#354 <https://github.com/askap-vast/vast-pipeline/pull/354>`_ fix, model: Updated Band model fields to floats
* `#346 <https://github.com/askap-vast/vast-pipeline/pull/346>`_ fix: fix JS9 overflow in measurement detail view
* `#349 <https://github.com/askap-vast/vast-pipeline/pull/349>`_ dep: Bump lodash from 4.17.15 to 4.17.20
* `#348 <https://github.com/askap-vast/vast-pipeline/pull/348>`_ dep: Bump django from 3.0.5 to 3.0.7 in /requirements
* `#344 <https://github.com/askap-vast/vast-pipeline/pull/344>`_ fix: fixed aladin init for all pages
* `#340 <https://github.com/askap-vast/vast-pipeline/pull/340>`_ break: rename pipeline folder to vast_pipeline
* `#342 <https://github.com/askap-vast/vast-pipeline/pull/342>`_ fix: Hotfix * fixed parquet path on job detail view
* `#336 <https://github.com/askap-vast/vast-pipeline/pull/336>`_ feat: Simbad/NED async cone search
* `#284 <https://github.com/askap-vast/vast-pipeline/pull/284>`_ fix: Update Aladin surveys with RACS and VAST
* `#333 <https://github.com/askap-vast/vast-pipeline/pull/333>`_ feat: auth to GitHub org, add logging and docstring
* `#325 <https://github.com/askap-vast/vast-pipeline/pull/325>`_ fix, feat: fix forced extraction using Dask bags backend
* `#334 <https://github.com/askap-vast/vast-pipeline/pull/334>`_ doc: better migration management explanation
* `#332 <https://github.com/askap-vast/vast-pipeline/pull/332>`_ fix: added clean to build task, removed commented lines
* `#322 <https://github.com/askap-vast/vast-pipeline/pull/322>`_ fix, model: add unique to image name, remove timestamp from image folder
* `#321 <https://github.com/askap-vast/vast-pipeline/pull/321>`_ feat: added css and js sourcemaps
* `#314 <https://github.com/askap-vast/vast-pipeline/pull/314>`_ feat: query form redesign, sesame resolver, coord validator
* `#318 <https://github.com/askap-vast/vast-pipeline/pull/318>`_ feat: Suppress astropy warnings
* `#317 <https://github.com/askap-vast/vast-pipeline/pull/317>`_ fix: Forced photometry fixes for #298 and #312
* `#316 <https://github.com/askap-vast/vast-pipeline/pull/316>`_ fix: fix migration file 0001_initial.py
* `#310 <https://github.com/askap-vast/vast-pipeline/pull/310>`_ fix: Fix run detail number of measurements display
* `#309 <https://github.com/askap-vast/vast-pipeline/pull/309>`_ fix: Added JS9 overlay filters and changed JS9 overlay behaviour on sources and measurements
* `#303 <https://github.com/askap-vast/vast-pipeline/pull/303>`_ fix: Fix write config feedback and validation
* `#306 <https://github.com/askap-vast/vast-pipeline/pull/306>`_ feat: Add config validation checks
* `#302 <https://github.com/askap-vast/vast-pipeline/pull/302>`_ fix: Fix RA correction for d3 celestial
* `#300 <https://github.com/askap-vast/vast-pipeline/pull/300>`_ fix: increase line limit for gunicorn server
* `#299 <https://github.com/askap-vast/vast-pipeline/pull/299>`_ fix: fix admin "view site" redirect
* `#294 <https://github.com/askap-vast/vast-pipeline/pull/294>`_ fix: Make lightcurves start at zero
* `#268 <https://github.com/askap-vast/vast-pipeline/pull/268>`_ feat: Production set up with static files and command
* `#291 <https://github.com/askap-vast/vast-pipeline/pull/291>`_ fix: Bug fix for forced_photom cluster allow_nan
* `#289 <https://github.com/askap-vast/vast-pipeline/pull/289>`_ fix: Fix broken UI run creation
* `#287 <https://github.com/askap-vast/vast-pipeline/pull/287>`_ fix: Fix forced measurement parquet files write
* `#286 <https://github.com/askap-vast/vast-pipeline/pull/286>`_ fix: compile JS9 without helper option
* `#285 <https://github.com/askap-vast/vast-pipeline/pull/285>`_ fix: Fix removing forced parquet and clear images from piperun
