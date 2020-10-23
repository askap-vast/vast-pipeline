VAST Pipeline
=============

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org/
    :alt: astropy

This repository holds the code of the Radio Transient detection pipeline for the VAST project.

Read Installation instructions. If you intend to contribute to/develop the code base please read and follow the guidelines. Detailed documentation on `Vast Pipeline Documentation <http://>`_.

Features
--------

* Code base in ``Python 3.6+``, recommended ``3.7``
* Source association/manipulations using ``Astropy4+`` and ``Pandas1+`` dataframe
* Association methods: basic (``Astropy`` crossmatch), advanced (search with a fixed distance), De Ruiter
* Flagging of "New Source" and "Related Source"
* Forced Extraction (Monitor) backward and forward in time
* Parallelization and scalability using Dask API (``Dask 2+``)
* Data exploration in modern ``Django3+`` Web App (Bootstrap 4)
* Accessing raw pipeline output data using ``.parquet`` and ``.arrow`` files
* Pipeline interface from command line (CLI) and via Web App
* Web App is served by ``Postgres12+`` with `Q3C plugin <https://github.com/segasai/q3c>`_


Screenshots and Previews
------------------------



Credits & Acknowledgements
--------------------------
This tool was developed by Sergio Pintaldi from the `Sydney Informatics Hub <https://informatics.sydney.edu.au>`_ – a core research facility of `The University of Sydney <https://www.sydney.edu.au/>`_ – together with Adam Stewart from the Sydney Institute for Astrophysics, School of Physics, Andrew O'Brien and David Kaplan from Department of Physics, University of Wisconsin-Milwaukee.

The developers thank the creators of `SB Admin 2 <https://github.com/StartBootstrap/startbootstrap-sb-admin-2>`_ to make the dashboard template freely available.

If using this dashboard in your research, please acknowledge the `Sydney Informatics Hub <https://informatics.sydney.edu.au>`_ in publications.

.. code-block::

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
