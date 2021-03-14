# VAST Pipeline

<!-- created with https://shields.io/category/monitoring -->
[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)
[![Nimbus](https://img.shields.io/website?down_color=red&down_message=offline&label=Nimbus&up_color=green&up_message=online&url=https%3A%2F%2Fdata.vast-survey.org%2Fpipeline%2F)](https://data.vast-survey.org/pipeline/)
![Tests](https://github.com/askap-vast/vast-pipeline/workflows/test-suite/badge.svg)
<!-- TODO: replace above with this below when repo is public -->
<!-- ![Tests](https://img.shields.io/github/workflow/status/askap-vast/vast-pipeline/test-suite/master?label=Test%20Suite&logo=github) -->

This repository holds the code of the Radio Transient detection pipeline for the VAST project.

[![VAST Pipeline Login](https://github.com/askap-vast/vast-pipeline/blob/master/docs/img/login.png)](https://github.com/askap-vast/vast-pipeline/blob/master/docs/img/login.png)

Please read the [Installation Instructions](https://vast-survey.org/vast-pipeline/quickstart/installation/). If you have any questions or feedback, we welcome you to open an [issue](https://github.com/askap-vast/vast-pipeline/issues). If you are interested in contributing to the code, please read and follow the [Contributing and Developing Guidelines](https://vast-survey.org/vast-pipeline/developing/intro/).

## Features

* Code base in `Python 3.6+`, recommended >= `3.7`
* Source association/manipulations using `Astropy4+` and `Pandas1+` dataframe
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

## Credits & Acknowledgements

This tool was developed by Sergio Pintaldi from the [Sydney Informatics Hub](https://informatics.sydney.edu.au) – a core research facility of [The University of Sydney](https://www.sydney.edu.au/) – together with Adam Stewart from the [Sydney Institute for Astronomy](https://sifa.sydney.edu.au/), Andrew O'Brien and David Kaplan from the [Department of Physics, University of Wisconsin-Milwaukee](https://uwm.edu/physics/research/astronomy-gravitation-cosmology/). Substantial contributions have been made by the [ADACS team](https://adacs.org.au/who-we-are/our-team/) Shibli Saleheen, David Liptai, Ella Xi Wang.

The developers thank the creators of [SB Admin 2](https://github.com/StartBootstrap/startbootstrap-sb-admin-2) to make the dashboard template freely available.

If using this tool in your research, please acknowledge the [Sydney Informatics Hub](https://informatics.sydney.edu.au) in publications.

```console

         /  /\        ___          /__/\
        /  /:/_      /  /\         \  \:\
       /  /:/ /\    /  /:/          \__\:\
      /  /:/ /::\  /__/::\      ___ /  /::\
     /__/:/ /:/\:\ \__\/\:\__  /__/\  /:/\:\
     \  \:\/:/~/:/    \  \:\/\ \  \:\/:/__\/
      \  \::/ /:/      \__\::/  \  \::/
       \__\/ /:/       /__/:/    \  \:\
         /__/:/ please \__\/      \  \:\
         \__\/ acknowledge your use\__\/
```
