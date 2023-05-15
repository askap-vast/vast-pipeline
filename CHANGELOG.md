# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), with an added `List of PRs` section and links to the relevant PRs on the individual updates. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/askap-vast/vast-pipeline/compare/v1.0.0...HEAD)

#### Added

- Added `n_new_sources` column to run model to store the number of new sources in a pipeline run [#676](https://github.com/askap-vast/vast-pipeline/pull/676).
- Added `MAX_CUTOUT_IMAGES` to the pipeline settings to limit the number of postage stamps displayed on the source detail page [#658](https://github.com/askap-vast/vast-pipeline/pull/658).
- Added run config option to skip calculating measurement pair metrics [#655](https://github.com/askap-vast/vast-pipeline/pull/655).
- Added support for Python 3.10 [#641](https://github.com/askap-vast/vast-pipeline/pull/641).
- Added documentation versioning [#627](https://github.com/askap-vast/vast-pipeline/pull/627).
- Added a ZTF cone search button on the source detail page [#626](https://github.com/askap-vast/vast-pipeline/pull/626).
- Added the 0-based index of each measurement to the image cutout card headers [#625](https://github.com/askap-vast/vast-pipeline/pull/625).
- Added Bokeh hover tooltip to measurement pair graph to display pair metrics [#625](https://github.com/askap-vast/vast-pipeline/pull/625).
- Added new VAST surveys (13-21) to the Aladin Lite panel [#622](https://github.com/askap-vast/vast-pipeline/pull/622).
- Added eta-V plot analysis page along with documentation [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Added thumbnails to light curve tooltips [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Added logfile dropdown selection to run detail page [#595](https://github.com/askap-vast/vast-pipeline/pull/595).
- Added datetime stamps to all log files [#595](https://github.com/askap-vast/vast-pipeline/pull/595).
- Added new log files for arrow file creation and restore run and added to run detail page [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Added restore run test [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Added new run status of `DEL`, `Deleting` [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Added documentation pages on new action buttons [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Added UI action buttons to run-detail page to allow arrow file generation, deletion and restoration [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Added try-except error capture on pre-run checks to correctly assign pipeline run as failed if an error occurs [#576](https://github.com/askap-vast/vast-pipeline/pull/576).
- Added support for ingesting Selavy catalogues in VOTable (XML) and CSV format [#565](https://github.com/askap-vast/vast-pipeline/pull/565)
- Added new commands: `initingest` and `ingestimages` [#544](https://github.com/askap-vast/vast-pipeline/pull/544)
- Added documentation on the data required to run the pipeline [#572](https://github.com/askap-vast/vast-pipeline/pull/572).
- Added support for ingesting Selavy catalogues in VOTable (XML) and CSV format [#565](https://github.com/askap-vast/vast-pipeline/pull/565).
- Added new commands: `initingest` and `ingestimages` [#544](https://github.com/askap-vast/vast-pipeline/pull/544).
- Added TNS cone search to the external search results on the source detail page [#557](https://github.com/askap-vast/vast-pipeline/pull/557).
- Added `HOME_DATA_ROOT` to the pipeline settings to override the OS default home directory location [#559](https://github.com/askap-vast/vast-pipeline/pull/559).
- Added processing spinner to source query table [#551](https://github.com/askap-vast/vast-pipeline/pull/551).
- Added `site_url` to the mkdocs config so static asset URLs have the correct base URL [#543](https://github.com/askap-vast/vast-pipeline/pull/543).
- Added basic linter to CI/CD [#546](https://github.com/askap-vast/vast-pipeline/pull/546)

#### Changed

- Updated GitHub actions Gr1N/setup-poetry to v7 [#665](https://github.com/askap-vast/vast-pipeline/pull/665).
- Changed lightcurve plot cursor hit-test mode from "vline" to "mouse" to avoid a regression in Bokeh [#652](https://github.com/askap-vast/vast-pipeline/pull/652).
- Updated Bokeh from v2.3.3 to v2.4.2 [#652](https://github.com/askap-vast/vast-pipeline/pull/652).
- Source query results table is no longer populated by default, a query must be submitted first [#638](https://github.com/askap-vast/vast-pipeline/pull/638).
- Bumped major versions of astropy (5.0) and pyarrow (7.0) [#641](https://github.com/askap-vast/vast-pipeline/pull/641).
- Addressed future pandas append deprecation, migrated all uses to pd.concat [#643](https://github.com/askap-vast/vast-pipeline/pull/643).
- Bumped all documentation dependancies to latest versions (incl. mkdocs-material minimum 8.2.4) [#627](https://github.com/askap-vast/vast-pipeline/pull/627).
- Changed GitHub workflows for new documentation versioning [#627](https://github.com/askap-vast/vast-pipeline/pull/627).
- Bumped Jinja2 to 3.0.3 to fix a Markupsafe error caused by a removed function [#634](https://github.com/askap-vast/vast-pipeline/pull/634).
- Dependancies updated using npm audit fix (non-breaking) [#620](https://github.com/askap-vast/vast-pipeline/pull/620).
- Refactored adding source to favourites button to use ajax to avoid page reload [#614](https://github.com/askap-vast/vast-pipeline/pull/614).
- Bumped test python versions to 3.7.12, 3.8.12 and 3.9.10 [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Bumped various dependencies using a fresh poetry.lock file [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Bumped bokeh packages to 2.3.3 [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Django-Q config variable `max_attempts` is configurable in the .env file [#595](https://github.com/askap-vast/vast-pipeline/pull/595).
- Replaced `models.MeasurementPair` model with a dataclass [#590](https://github.com/askap-vast/vast-pipeline/pull/590).
- Django-Q config variables `timeout` and `retry` are configurable in the .env file [#589](https://github.com/askap-vast/vast-pipeline/pull/589).
- Changed restore run command to only allow one run as input [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Changed existing documentation pages to reflect new buttons [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Moved creation of output backup files to occur before the config check [#576](https://github.com/askap-vast/vast-pipeline/pull/576).
- Association test data updated with d2d fix [#574](https://github.com/askap-vast/vast-pipeline/pull/574).
- Removed the timezone from the Timestamps being written to the the arrow file as this causes problems with vaex [#571](https://github.com/askap-vast/vast-pipeline/pull/571).
- Reduced the memory footprint for computing the ideal source coverages by sky regions [#555](https://github.com/askap-vast/vast-pipeline/pull/555).
- Gulp will only read `webinterface/.env` if the required vars are undefined in the current environment [#548](https://github.com/askap-vast/vast-pipeline/pull/548).

#### Fixed

- Updated test and lint workflows to use `ubuntu-latest` [#687](https://github.com/askap-vast/vast-pipeline/pull/687).
- Fixed link to JupyterHub [#676](https://github.com/askap-vast/vast-pipeline/pull/676).
- Ensure Image models are not created if the catalogue ingest fails [#648](https://github.com/askap-vast/vast-pipeline/pull/648).
- Fixed run failures caused by attempting to force fit images with empty catalogues [#653](https://github.com/askap-vast/vast-pipeline/pull/653).
- Fixed a Bokeh regression that requires LabelSet values to be strings [#652](https://github.com/askap-vast/vast-pipeline/pull/652).
- Fixed deprecation warning on astroquery Ned import [#644](https://github.com/askap-vast/vast-pipeline/pull/644).
- Fixed a regression from pandas==1.4.0 that caused empty groups to be passed to an apply function in parallel association [#642](https://github.com/askap-vast/vast-pipeline/pull/642).
- Fixed docs issue that stopped serializers and views being shown in the code reference [#627](https://github.com/askap-vast/vast-pipeline/pull/627).
- Fixed broken links to external search results from NED by URI encoding source names [#633](https://github.com/askap-vast/vast-pipeline/pull/633).
- Fixed a regression from pandas==1.4.0 that caused empty groups to be passed to an apply function [#632](https://github.com/askap-vast/vast-pipeline/pull/632).
- Fixed source names to be IAU compliant [#618](https://github.com/askap-vast/vast-pipeline/pull/618).
- Fixed broken NED links for coordinates with many decimal places [#623](https://github.com/askap-vast/vast-pipeline/pull/623).
- Added an error handler for the external source queries (e.g. SIMBAD) [#616](https://github.com/askap-vast/vast-pipeline/pull/616).
- Stopped JS9 from changing the page titles [#597](https://github.com/askap-vast/vast-pipeline/pull/597).
- Fixed regression issues with pandas 1.4 [#586](https://github.com/askap-vast/vast-pipeline/pull/586).
- Fixed config being copied before run was confirmed to actually go ahead for existing runs [#595](https://github.com/askap-vast/vast-pipeline/pull/595).
- Fixed forced measurements being removed from associations during the restore run process [#600](https://github.com/askap-vast/vast-pipeline/pull/600).
- Fixed measurement FITS cutout bug [#588](https://github.com/askap-vast/vast-pipeline/pull/588).
- Fixed removal of image and sky region objects when a run is deleted [#585](https://github.com/askap-vast/vast-pipeline/pull/585).
- Fixed testing pandas equal deprecation warning [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Fixed restore run relations issue [#580](https://github.com/askap-vast/vast-pipeline/pull/580).
- Fixed logic for full re-run requirement when UI run is being re-run from an error status [#576](https://github.com/askap-vast/vast-pipeline/pull/576).
- Fixed d2d not being carried through the advanced association process [#574](https://github.com/askap-vast/vast-pipeline/pull/574).
- Fixed old dictionary references in the documentation run config page [#572](https://github.com/askap-vast/vast-pipeline/pull/572).
- Fixed a regression from pandas=1.3.0 that caused non-numeric columns to be dropped after a groupby sum operation [#567](https://github.com/askap-vast/vast-pipeline/pull/567).
- Fixed permission error for regular users when trying to launch an initialised run [#563](https://github.com/askap-vast/vast-pipeline/pull/563).
- Fixed outdated installation link in README [#543](https://github.com/askap-vast/vast-pipeline/pull/543).

#### Removed

- Removed sky coverage plot from homepage [#676](https://github.com/askap-vast/vast-pipeline/pull/676).
- Removed various counts from homepage [#676](https://github.com/askap-vast/vast-pipeline/pull/676).
- Removed support for Python 3.7 [#641](https://github.com/askap-vast/vast-pipeline/pull/641).
- Removed Measurements table page and measurements table from run detail page [#636](https://github.com/askap-vast/vast-pipeline/pull/636).
- Removed the unique constraint on `models.Measurement.name` [#583](https://github.com/askap-vast/vast-pipeline/pull/583).

#### List of PRs

- [#687](https://github.com/askap-vast/vast-pipeline/pull/687): fix: Updated test and lint workflows ubuntu version.
- [#676](https://github.com/askap-vast/vast-pipeline/pull/676): Removed home counts and new source count.
- [#665](https://github.com/askap-vast/vast-pipeline/pull/665): Update Gr1N/setup-poetry to v7.
- [#658](https://github.com/askap-vast/vast-pipeline/pull/658): feat: Add MAX_CUTOUT_IMAGES setting.
- [#655](https://github.com/askap-vast/vast-pipeline/pull/655): feat: Add run config option to disable measurement pairs.
- [#648](https://github.com/askap-vast/vast-pipeline/pull/648): fix: make Image and Measurement creation atomic together.
- [#653](https://github.com/askap-vast/vast-pipeline/pull/653): fix: Allow forced fitting on images with empty catalogues.
- [#652](https://github.com/askap-vast/vast-pipeline/pull/652): dep, fix: Bump bokeh 2.4.2.
- [#644](https://github.com/askap-vast/vast-pipeline/pull/644): fix: Fix astroquery Ned import deprecation.
- [#638](https://github.com/askap-vast/vast-pipeline/pull/638): feat: Support defer loading of dataTables data.
- [#641](https://github.com/askap-vast/vast-pipeline/pull/641): dep: Drop Python 3.7 and dependency refresh.
- [#643](https://github.com/askap-vast/vast-pipeline/pull/643): fix: Addressed pandas DataFrame.append deprecation.
- [#642](https://github.com/askap-vast/vast-pipeline/pull/642): fix: Fix empty groups in parallel association.
- [#636](https://github.com/askap-vast/vast-pipeline/pull/636): fix, doc: Remove excessive measurement tables.
- [#627](https://github.com/askap-vast/vast-pipeline/pull/627): dep, docs: Documentation update and versioning.
- [#633](https://github.com/askap-vast/vast-pipeline/pull/633): fix: URI encode NED object names.
- [#632](https://github.com/askap-vast/vast-pipeline/pull/632): fix: skip empty groups in new sources groupby-apply.
- [#634](https://github.com/askap-vast/vast-pipeline/pull/634): dep: bump Jinja2 to v3.
- [#626](https://github.com/askap-vast/vast-pipeline/pull/626): feat: Add a ZTF cone search link.
- [#618](https://github.com/askap-vast/vast-pipeline/pull/618): fix: Produce IAU compliant source names.
- [#625](https://github.com/askap-vast/vast-pipeline/pull/625): feat: Pair metrics hover tooltip.
- [#620](https://github.com/askap-vast/vast-pipeline/pull/620): dep: Non-breaking npm audit fix update.
- [#622](https://github.com/askap-vast/vast-pipeline/pull/622): feat: Updated Aladin VAST surveys.
- [#623](https://github.com/askap-vast/vast-pipeline/pull/623): fix: fixed NED links.
- [#616](https://github.com/askap-vast/vast-pipeline/pull/616): fix: added error handling to external queries.
- [#614](https://github.com/askap-vast/vast-pipeline/pull/614): feat: Refactored add to favourites button to avoid refresh.
- [#597](https://github.com/askap-vast/vast-pipeline/pull/597): fix: Update detail page titles.
- [#586](https://github.com/askap-vast/vast-pipeline/pull/586): feat, dep, doc: Add an eta-v analysis page for the source query.
- [#595](https://github.com/askap-vast/vast-pipeline/pull/595): fix: Add date and time stamp to log files.
- [#600](https://github.com/askap-vast/vast-pipeline/pull/600): fix: Fixed restore run forced measurements associations.
- [#590](https://github.com/askap-vast/vast-pipeline/pull/590): fix: Remove MeasurementPair model.
- [#589](https://github.com/askap-vast/vast-pipeline/pull/589): fix: expose django-q timeout and retry to env vars.
- [#588](https://github.com/askap-vast/vast-pipeline/pull/588): fix: change cutout endpoint to use measurement ID.
- [#585](https://github.com/askap-vast/vast-pipeline/pull/585): fix: Clean up m2m related objects when deleting a run.
- [#583](https://github.com/askap-vast/vast-pipeline/pull/583): fix: remove unique constraint from Measurement.name.
- [#580](https://github.com/askap-vast/vast-pipeline/pull/580): feat, fix, doc: Added UI run action buttons.
- [#576](https://github.com/askap-vast/vast-pipeline/pull/576): fix: Fixed UI re-run from errored status.
- [#574](https://github.com/askap-vast/vast-pipeline/pull/574): fix: Fixed d2d assignment in advanced association.
- [#572](https://github.com/askap-vast/vast-pipeline/pull/572): doc: Added required data page to documentation.
- [#571](https://github.com/askap-vast/vast-pipeline/pull/571): fix: Removed timezone from measurements arrow file time column
- [#565](https://github.com/askap-vast/vast-pipeline/pull/565): feat: added support for reading selavy VOTables and CSVs.
- [#567](https://github.com/askap-vast/vast-pipeline/pull/567): fix: fixed pandas=1.3.0 groupby sum regression.
- [#563](https://github.com/askap-vast/vast-pipeline/pull/563): fix: fixed launch run user permission bug.
- [#544](https://github.com/askap-vast/vast-pipeline/pull/544): feat: new command to ingest images without running the full pipeline.
- [#557](https://github.com/askap-vast/vast-pipeline/pull/557): feat: Add TNS external search for sources.
- [#559](https://github.com/askap-vast/vast-pipeline/pull/559): feat: added HOME_DATA_ROOT setting.
- [#555](https://github.com/askap-vast/vast-pipeline/pull/555): fix: compute ideal source coverage with astropy xmatch.
- [#551](https://github.com/askap-vast/vast-pipeline/pull/551): feat: added processing spinner to source query table.
- [#550](https://github.com/askap-vast/vast-pipeline/pull/550): fix: missing changelog entry
- [#548](https://github.com/askap-vast/vast-pipeline/pull/548): fix: only read .env if required vars are undefined.
- [#546](https://github.com/askap-vast/vast-pipeline/pull/546): feat, fix: remove unused imports, and added basic linter during CI/CD.
- [#543](https://github.com/askap-vast/vast-pipeline/pull/543): fix, doc: Fix README link and documentation 404 assets.

## [1.0.0](https://github.com/askap-vast/vast-pipeline/releases/v1.0.0) (2021-05-21)

#### Added

- When searching by source names, any "VAST" prefix on the name will be silently removed to make searching for published VAST sources easier [#536](https://github.com/askap-vast/vast-pipeline/pull/536).
- Added acknowledgements and help section to docs [#535](https://github.com/askap-vast/vast-pipeline/pull/535).
- Added `vast_pipeline/_version.py` to store the current software version and updated release documentation [#532](https://github.com/askap-vast/vast-pipeline/pull/532).
- Added created and last updated dates to doc pages using mkdocs-git-revision-date-localized-plugin [#514](https://github.com/askap-vast/vast-pipeline/pull/514).
- Added support for glob expressions when specifying input files in the run config file [#504](https://github.com/askap-vast/vast-pipeline/pull/504)
- Added `DEFAULT_AUTO_FIELD` to `settings.py` to silence Django 3.2 warnings [#507](https://github.com/askap-vast/vast-pipeline/pull/507)
- Added lightgallery support for all images in the documentation [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Added new entries in the documentation contributing section [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Added new entries in the documentation FAQ section [#491](https://github.com/askap-vast/vast-pipeline/pull/491).
- Added new home page for documentation [#491](https://github.com/askap-vast/vast-pipeline/pull/491).
- Added dark mode switch on documentation [#487](https://github.com/askap-vast/vast-pipeline/pull/487).
- Added .env file information to documentation [#487](https://github.com/askap-vast/vast-pipeline/pull/487).
- Added further epoch based association information to documentation page [#487](https://github.com/askap-vast/vast-pipeline/pull/487).
- Added script to auto-generate code reference documentation pages [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Added code reference section to documentation [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Added new pages and sections to documentation [#471](https://github.com/askap-vast/vast-pipeline/pull/471)
- Added `requirements/environment.yml` so make it easier for Miniconda users to get the non-Python dependencies [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Added `pyproject.toml` and `poetry.lock` [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Added `init-tools/init-db.py` [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Added image add mode run restore command 'restorepiperun' [#463](https://github.com/askap-vast/vast-pipeline/pull/463)
- Added documentation folder and files for `mkdocs` and CI [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Added add image to existing run feature [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Added networkx to base reqiurements [#460](https://github.com/askap-vast/vast-pipeline/pull/460).
- Added CI/CD workflow to run tests on pull requests [#446](https://github.com/askap-vast/vast-pipeline/pull/446)
- Added basic regression tests [#425](https://github.com/askap-vast/vast-pipeline/pull/425)
- Added image length validation for config [#425](https://github.com/askap-vast/vast-pipeline/pull/425)

#### Changed

- Changed source naming convention to `Jhhmmss.s(+/-)ddmmss` to match VAST-P1 paper (Murphy, et al. 2021) convention [#536](https://github.com/askap-vast/vast-pipeline/pull/536)
- Updated npm packages to resolve dependabot security alert [#533](https://github.com/askap-vast/vast-pipeline/pull/533).
- Updated homepage text to reflect new features and documentation [#534](https://github.com/askap-vast/vast-pipeline/pull/534).
- Changed layout of source detail page [#526](https://github.com/askap-vast/vast-pipeline/pull/526).
- Updated mkdocs-material to 7.1.4 for native creation date support [#518](https://github.com/askap-vast/vast-pipeline/pull/518).
- Updated developing docs to specify the main development branch as dev instead of master [#521](https://github.com/askap-vast/vast-pipeline/pull/521).
- Updated tests to account for relation fix [#510](https://github.com/askap-vast/vast-pipeline/pull/510).
- All file examples in docs are now enclosed in an example admonition [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Further changes to layout of documentation [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Changed arrow file generation from `vaex` to `pyarrow` [#503](https://github.com/askap-vast/vast-pipeline/pull/503).
- Changed layout of documentation to use tabs [#491](https://github.com/askap-vast/vast-pipeline/pull/491).
- Dependabot: Bump y18n from 3.2.1 to 3.2.2 [#482](https://github.com/askap-vast/vast-pipeline/pull/482).
- Replaced run config .py format with .yaml [#483](https://github.com/askap-vast/vast-pipeline/pull/483).
- Changed docs VAST logo to icon format to avoid stretched appearence [#487](https://github.com/askap-vast/vast-pipeline/pull/487).
- Bumped Browsersync from 2.26.13 to 2.26.14 [#481](https://github.com/askap-vast/vast-pipeline/pull/481).
- Dependabot: Bump prismjs from 1.22.0 to 1.23.0 [#469](https://github.com/askap-vast/vast-pipeline/pull/469).
- Changed non-google format docstrings to google format [#480](https://github.com/askap-vast/vast-pipeline/pull/480).
- Changed some documentation layout and updated content [#471](https://github.com/askap-vast/vast-pipeline/pull/471).
- Changed the `vaex` dependency to `vaex-arrow` [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Set `CREATE_MEASUREMENTS_ARROW_FILES = True` in the basic association test config [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Bumped minimum Python version to 3.7.1 [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Replaced npm package `gulp-sass` with `@mr-hope/gulp-sass`, a fork which drops the dependency on the deprecated `node-sass` which is difficult to install [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Changed the installation documentation to instruct users to use a PostgreSQL Docker image with Q3C already installed [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Changed 'cmd' flag in run pipeline to 'cli' [#466](https://github.com/askap-vast/vast-pipeline/pull/466).
- Changed `CONTRIBUTING.md` and `README.md` [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Changed forced extraction name suffix to run id rather than datetime [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Changed tests to run on smaller cutouts [#443](https://github.com/askap-vast/vast-pipeline/pull/443)
- Changed particles style on login page [#459](https://github.com/askap-vast/vast-pipeline/pull/459).
- Dependabot: Bump ini from 1.3.5 to 1.3.8 [#436](https://github.com/askap-vast/vast-pipeline/pull/436)

#### Fixed

- Fixed the broken link to the image detail page on measurement detail pages [#528](https://github.com/askap-vast/vast-pipeline/pull/528).
- Fixed simbad and ned external search results table nan values [#523](https://github.com/askap-vast/vast-pipeline/pull/523).
- Fixed inaccurate total results reported by some paginators [#517](https://github.com/askap-vast/vast-pipeline/pull/517).
- Removed excess whitespace from coordinates that get copied to the clipboard [#515](https://github.com/askap-vast/vast-pipeline/pull/515)
- Fixed rogue relations being created during one-to-many functions [#510](https://github.com/askap-vast/vast-pipeline/pull/510).
- Fixed JS9 regions so that the selected source components are always on top [#508](https://github.com/askap-vast/vast-pipeline/pull/508)
- Fixed docstring in config.py [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Fixed arrow files being generated via the website [#503](https://github.com/askap-vast/vast-pipeline/pull/503).
- Fixed a bug that returned all sources when performing a cone search where one of the coords = 0 [#501](https://github.com/askap-vast/vast-pipeline/pull/501)
- Fixed the missing hover tool for lightcurve plots of non-variable sources [#493](https://github.com/askap-vast/vast-pipeline/pull/493)
- Fixed the default Dask multiprocessing context to "fork" [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
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

- Removed `SURVEYS_WORKING_DIR` from settings and env file [#538](https://github.com/askap-vast/vast-pipeline/pull/538).
- Removed `default_survey` from run configuration file [#538](https://github.com/askap-vast/vast-pipeline/pull/538).
- Removed importsurvey command and catalogue.py [#538](https://github.com/askap-vast/vast-pipeline/pull/538).
- Removed SurveySource, Survey and SurveySourceQuerySet models [#538](https://github.com/askap-vast/vast-pipeline/pull/538).
- Removed email and Slack links from docs footer [#535](https://github.com/askap-vast/vast-pipeline/pull/535).
- Removed bootstrap as the required version is bundled with startbootstrap-sb-admin-2 [#533](https://github.com/askap-vast/vast-pipeline/pull/533).
- Removed `docs/readme.md` softlink as it is no longer used [#494](https://github.com/askap-vast/vast-pipeline/pull/494).
- Removed `vaex-arrow` from the dependancies [#503](https://github.com/askap-vast/vast-pipeline/pull/503).
- Removed `requirements/*.txt` files. Development dependency management moved to Poetry [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Removed `init-tools/init-db.sh` [#472](https://github.com/askap-vast/vast-pipeline/pull/472).
- Removed `INSTALL.md`, `PROFILE.md` and `static/README.md` [#433](https://github.com/askap-vast/vast-pipeline/pull/433)
- Removed aplpy from base requirements [#460](https://github.com/askap-vast/vast-pipeline/pull/460).

#### List of PRs

- [#538](https://github.com/askap-vast/vast-pipeline/pull/538) feat: Removed survey source models, commands and references.
- [#536](https://github.com/askap-vast/vast-pipeline/pull/536) feat: changed source naming convention.
- [#535](https://github.com/askap-vast/vast-pipeline/pull/535) doc: added help and acknowledgement doc page.
- [#534](https://github.com/askap-vast/vast-pipeline/pull/534) feat: Update homepage text.
- [#532](https://github.com/askap-vast/vast-pipeline/pull/532) feat, doc: Versioning.
- [#533](https://github.com/askap-vast/vast-pipeline/pull/533) dep: updated npm deps; removed bootstrap.
- [#528](https://github.com/askap-vast/vast-pipeline/pull/528) fix: fixed broken image detail link.
- [#526](https://github.com/askap-vast/vast-pipeline/pull/526) feat: Updated source detail page layout.
- [#518](https://github.com/askap-vast/vast-pipeline/pull/518) dep: Updated mkdocs-material for native creation date support.
- [#523](https://github.com/askap-vast/vast-pipeline/pull/523) fix: Fixed external search results table nan values.
- [#521](https://github.com/askap-vast/vast-pipeline/pull/521) doc: update doc related to default dev branch.
- [#517](https://github.com/askap-vast/vast-pipeline/pull/517) fix: pin djangorestframework-datatables to 0.5.1.
- [#515](https://github.com/askap-vast/vast-pipeline/pull/515) fix: remove linebreaks from coordinates.
- [#514](https://github.com/askap-vast/vast-pipeline/pull/514) dep: Added created and updated dates to doc pages.
- [#510](https://github.com/askap-vast/vast-pipeline/pull/510) fix: Fix rogue relations.
- [#508](https://github.com/askap-vast/vast-pipeline/pull/508) fix: Draw selected source components on top in JS9.
- [#504](https://github.com/askap-vast/vast-pipeline/pull/504) feat: Add glob expression support to yaml run config.
- [#507](https://github.com/askap-vast/vast-pipeline/pull/507) fix: set default auto field model.
- [#494](https://github.com/askap-vast/vast-pipeline/pull/494) doc, dep: Docs: Added lightgallery support, layout update, minor fixes and additions.
- [#503](https://github.com/askap-vast/vast-pipeline/pull/503) fix, dep: Change arrow file generation from vaex to pyarrow.
- [#501](https://github.com/askap-vast/vast-pipeline/pull/501) fix: fix broken cone search when coord = 0
- [#491](https://github.com/askap-vast/vast-pipeline/pull/491) doc: Updated the docs layout, home page and FAQs.
- [#493](https://github.com/askap-vast/vast-pipeline/pull/493) fix: Fix bokeh hover tool for lightcurve plots.
- [#482](https://github.com/askap-vast/vast-pipeline/pull/482) dep: Bump y18n from 3.2.1 to 3.2.2.
- [#483](https://github.com/askap-vast/vast-pipeline/pull/483) feat: replace run config .py files with .yaml.
- [#487](https://github.com/askap-vast/vast-pipeline/pull/487) doc: Minor documentation improvements.
- [#481](https://github.com/askap-vast/vast-pipeline/pull/481) dep: Bump Browsersync from 2.26.13 to 2.26.14.
- [#469](https://github.com/askap-vast/vast-pipeline/pull/469) dep: Bump prismjs from 1.22.0 to 1.23.0.
- [#480](https://github.com/askap-vast/vast-pipeline/pull/480) feat: Code reference documentation update.
- [#471](https://github.com/askap-vast/vast-pipeline/pull/471) feat: Documentation update.
- [#472](https://github.com/askap-vast/vast-pipeline/pull/472) feat: Simplify install.
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

## [0.2.0](https://github.com/askap-vast/vast-pipeline/releases/v0.2.0) (2020-11-30)

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

## [0.1.0](https://github.com/askap-vast/vast-pipeline/releases/v0.1.0) (2020-09-27)

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
