# VAST Pipeline
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13927016.svg)](https://doi.org/10.5281/zenodo.13927016)
[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)
![Tests](https://github.com/askap-vast/vast-pipeline/workflows/test-suite/badge.svg)
[![documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg?style=flat)](https://vast-survey.org/vast-pipeline/)
[![Nimbus](https://img.shields.io/website?down_color=red&down_message=offline&label=Nimbus&up_color=green&up_message=online&url=https%3A%2F%2Fdev.pipeline.vast-survey.org)](https://dev.pipeline.vast-survey.org)
<!-- created with https://shields.io/category/monitoring -->


<!-- TODO: replace above with this below when repo is public -->
<!-- ![Tests](https://img.shields.io/github/workflow/status/askap-vast/vast-pipeline/test-suite/master?label=Test%20Suite&logo=github) -->

This repository holds the code of the VAST Pipeline, a radio transient detection pipeline for the ASKAP survey science project, VAST.

Please read the [Installation Instructions](https://vast-survey.org/vast-pipeline/v1.0.0/gettingstarted/installation/). If you have any questions or feedback, we welcome you to open an [issue](https://github.com/askap-vast/vast-pipeline/issues). If you are interested in contributing to the code, please read and follow the [Contributing and Developing Guidelines](https://vast-survey.org/vast-pipeline/v1.0.0/developing/intro/).

If using this tool in your research, please cite [10.5281/zenodo.13927015](https://doi.org/10.5281/zenodo.13927016).

## Features

* Code base in `Python 3.8+`
* Source association/manipulations using `Astropy5+` and `Pandas1+` dataframe
* Association methods: basic (`Astropy` crossmatch), advanced (search with a fixed distance), De Ruiter
* Flagging of "New Source" and "Related Source"
* Forced Extraction (Monitor) backward and forward in time
* Parallelization and scalability using Dask API (`Dask 2+`)
* Data exploration in modern `Django3+` Web App (Bootstrap 4)
* Accessing raw pipeline output data using `.parquet` and `.arrow` files
* Pipeline interface from command line (CLI) and via Web App
* Web App is served by `Postgres12+` with [Q3C plugin](https://github.com/segasai/q3c)

## Screenshots and Previews

[![VAST Pipeline Overview](https://github.com/askap-vast/vast-pipeline/blob/master/docs/img/vast_pipeline_overview1.gif)](https://github.com/askap-vast/vast-pipeline/blob/master/docs/img/vast_pipeline_overview1.gif)

## Contributors

### Active
* Dougal Dobie – [Sydney Institute for Astronomy](https://sifa.sydney.edu.au/) and [OzGrav](https://www.ozgrav.org)
* Tom Mauch – [Sydney Informatics Hub](https://informatics.sydney.edu.au)
* Adam Stewart – [Sydney Institute for Astronomy](https://sifa.sydney.edu.au/)

### Former
* Sergio Pintaldi – [Sydney Informatics Hub](https://informatics.sydney.edu.au)
* Andrew O'Brien – [Department of Physics, University of Wisconsin-Milwaukee](https://uwm.edu/physics/research/astronomy-gravitation-cosmology/)
* Tara Murphy – [Sydney Institute for Astronomy](https://sifa.sydney.edu.au/)
* David Kaplan – [Department of Physics, University of Wisconsin-Milwaukee](https://uwm.edu/physics/research/astronomy-gravitation-cosmology/)
* Shibli Saleheen – [ADACS](https://adacs.org.au/)
* David Liptai – [ADACS](https://adacs.org.au/)
* Ella Xi Wang – [ADACS](https://adacs.org.au/)

## Acknowledgements

The VAST Pipeline development was supported by:

* The Australian Research Council through grants FT150100099 and DP190100561.
* The Australian Research Council Centre of Excellence for Gravitational Wave Discovery (OzGrav), project numbers CE170100004 and CE230100016.
* The Sydney Informatics Hub (SIH), a core research facility at the University of Sydney.
* Software support resources awarded under the Astronomy Data and Computing Services (ADACS) Merit Allocation Program. ADACS is funded from the Astronomy National Collaborative Research Infrastructure Strategy (NCRIS) allocation provided by the Australian Government and managed by Astronomy Australia Limited (AAL).
* NSF grant AST-1816492.

We also acknowledge the [LOFAR Transients Pipeline (TraP)](https://ascl.net/1412.011) ([Swinbank, et al. 2015](https://ui.adsabs.harvard.edu/abs/2015A%26C....11...25S/abstract)) from which various concepts and design choices have been implemented in the VAST Pipeline.

The developers thank the creators of [SB Admin 2](https://github.com/StartBootstrap/startbootstrap-sb-admin-2) to make the dashboard template freely available.
