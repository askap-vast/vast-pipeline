# Frequently Asked Questions

### Can the VAST Pipeline be used with images from other telescopes?

The base answer to this question is that the pipeline has been designed specifically for ASKAPsoft and ASKAPpipeline products, so compatibility with data from other telescopes is not supported.

However, it's important to remember that the pipeline performs no source extraction itself, instead it reads in source catalogues that is expected to be in the format of the output of the `Selavy` source extractor.
As seen from the [Image Ingest page](design/imageingest.md), the pipeline does not use any special or out of the ordinary FITS headers when reading the images, and the only inputs required are the images, catalogues, noise images and background images - which are standard products. Hence, the real answer to this question is yes, if one of the following is performed:

* Run the `Selavy` source extractor on the images to process.
* Convert the component output from a different source extractor to match that of the [`Selavy` component file](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/postprocessing.html#output-files){:target="_blank"}.

The pipeline was also designed in a way such that other source extractor 'translators' could be plugged into the pipeline. 
So a further option is to develop new translators such that the pipeline can read in output from other source extractors. 
The translators can be found in [`vast_pipeline/surveys/translators.py`](reference/survey/translators.md).
Please open a discussion or issue on GitHub if you intend to give this a go!

!!! bug
    In reading the code recently I have a suspicion the FITS reading code is reliant on the `TELESCOP` FITS header being equal to `ASKAP`. 
    This is unintentional as there is nothing special about the FITS headers being read. 
    Worth to check if anyone goes down this path. - Adam, March 2021.

### Does the pipeline support any other Stokes products such as Stokes V?

Currently the pipeline only supports Stokes I data.

Users can view Stokes V HIPS maps of the RACS and VAST surveys in the Aladin Lite tool on the [source detail page](exploringwebsite/sourcedetail.md).

The support of Stokes V is [planned in a future update](https://github.com/askap-vast/vast-pipeline/issues/223){:target="_blank"}.

### Can the pipeline handle multi-frequency datasets?

Currently the pipeline does not support multi-frequency datasets. Any images that are put through in a run are assumed by the pipeline to be directly comparable to one another.
For example, all variability metrics are calculated directly on the fluxes provided from the source catalogues.

Multi-frequency support is [planned in a future update](https://github.com/askap-vast/vast-pipeline/issues/467).


