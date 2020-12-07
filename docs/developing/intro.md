# Contributing and Developing Guidelines

This section explains how to contribute to the project code base and collaborate on GitHub platform. A very exahustive set of general guidelines can be follow [here](https://github.com/apache/incubator-superset/blob/master/CONTRIBUTING.md), but I think the following will suffice for our purpose. The next sections describes:

* [GitHub Platform](github.md)
* [Local Development Enviroment](localdevenv.md)
* [Tests](tests.md)
* [Docs](docsdev.md)
* [Bechmarks](profiling.md)

## Terminology

These below is the terminology used to identify pipeline objects.

* Pipeline run (or "Run") -> Pipeline run instance, also referred as `run, p_run, piperun, pipe_run, ...` in the code
* Measurement -> the extracted measurement from the source finder of a single astrophysical source from an image, referred in the code as `measurement(s), meas, ...`
* Source -> A collection of single measurements for the same astrophysical source, referred as `src, source, ...` in the code

