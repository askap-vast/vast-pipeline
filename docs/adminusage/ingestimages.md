# Standalone Image Ingestion

Administrators have the added option of ingesting new images via the command line, without running the full pipeline.

!!! note
    Currently, when non-admin users run the pipeline, any images listed in the configuration that do not exist in the database will be processed and uploaded to the database. Hence, it is not a requirement to ingest images using this process before a run is processed that uses new images.

The relevant command is [`ingestimages`](../cli/#ingestimages), which requires and ingest configuration file as input.
The configuration file must contain the images to be listed, as well as a subset of options from the main [run configuration](../../using/runconfig) file.

In particular, along with the images to be ingested, the configuration requires the following options:

**`measurements.condon_errors`**
Boolean. Calculate the Condon errors of the extractions when read in from the source extraction file. If `False` then the errors directly from the source finder output are used. Recommended to set to `True` for selavy extractions. Defaults to `True`.

**`measurements.selavy_local_rms_fill_value`**
Float. Value to substitute for the `local_rms` parameter in selavy extractions if a `0.0` value is found. Unit is mJy. Defaults to `0.2`.

**`measurements.ra_uncertainty`**
Float. Defines an uncertainty error to the RA that will be added in quadrature to the existing source extraction error. Used to represent a systematic positional error. Unit is arcseconds. Defaults to 1.0.

**`measurements.dec_uncertainty`**
Float. Defines an uncertainty error to the Dec that will be added in quadrature to the existing source extraction error. Used to represent systematic positional error. Unit is arcseconds. Defaults to 1.0.

!!! example "ingest_config.yaml"
    ```yaml
    # This file is used for ingest only mode
    # It specifies the images to be processed and the relevant
    # settings to be used.

    inputs:
        # NOTE: all the inputs must match with each other, i.e. the catalogue for the first
        # input image (inputs.image[0]) must be the first input catalogue (inputs.selavy[0])
        # and so on.
        image:
        # list input images here, e.g. (note the leading hyphens)
            glob: ./data/epoch0?.fits

        selavy:
        # list input selavy catalogues here, as above with the images
            glob: ./data/epoch0?.selavy.components.txt

        noise:
        # list input noise (rms) images here, as above with the images
            glob: ./data/epoch0?.noiseMap.fits

        # Required only if source_monitoring.monitor is true, otherwise optional. If not providing
        # background images, remove the entire background section below.
        # background:
        # list input background images here, as above with the images

    measurements:
        # Replace the selavy errors with Condon (1997) errors.
        condon_errors: True

        # Sometimes the local rms for a source is reported as 0 by selavy.
        # Choose a value to use for the local rms in these cases in mJy/beam.
        selavy_local_rms_fill_value: 0.2

        # The positional uncertainty of a measurement is in reality the fitting errors and the
        # astrometric uncertainty of the image/survey/instrument combined in quadrature.
        # These two parameters are the astrometric uncertainty in RA/Dec and they may be different.
        ra_uncertainty: 1 # arcsec
        dec_uncertainty: 1  # arcsec

    ```
