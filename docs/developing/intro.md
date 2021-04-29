# Contributing and Developing Guidelines

This section explains how to contribute to the project code base and collaborate on GitHub platform.
Please use the section navigator to left to visit pages for specific details on areas of development.

## Terminology

These below is the terminology used to identify pipeline objects.

* Pipeline run (or "Run") -> Pipeline run instance, also referred as `run, p_run, piperun, pipe_run, ...` in the code
* Measurement -> the extracted measurement from the source finder of a single astrophysical source from an image, referred in the code as `measurement(s), meas, ...`
* Source -> A collection of single measurements for the same astrophysical source, referred as `src, source, ...` in the code

## Docstrings

All docstrings must be done using the [Google format](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html){target="_blank"} to ensure compatibility with the documentation.