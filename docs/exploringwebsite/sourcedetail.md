# Source Detail

This page presents all the information about the selected source, including a light curve and cutouts of all the measurements that are associated to the source.

![!Source detail page.](../img/source-detail1.png){: loading=lazy }

## Star, SIMBAD, NED, ZTF, Previous & Next Buttons

These buttons do the following:

* **Star**: Adds the source to the user's favourites, see [Source Tags and Favourites](sourcetagsfavs.md).
* **SIMBAD**: Performs a cone search on SIMBAD with a radius of 10 arcmin centered on the source location.
* **NED**: Performs a cone search on NED with a radius of 10 arcmin centered on the source location.
* **ZTF**: Performs a cone search for optical transient alerts from the Zwicky Transient Facility (ZTF) with a radius of 10 arcsec centered on the source location.
* **Previous**: Navigates to the previous source that was returned in the source query.
* **Next**: Navigates to the next source that was returned in the source query

## Details

A text representation of details of the source.

## First Detection Postage Stamp

The JS9 viewer is used to show the postage stamp FITS image (cutout) of the first source-finder detection for this source. Cutouts for each measurement are shown further down the page.

## Aladin Lite Viewer

[Aladin Lite Documentation](https://aladin.u-strasbg.fr/AladinLite/doc/){ target=_blank }.

The central panel contains an Aladin Lite viewer, which by default displays the HIPS image from the [Rapid ASKAP Continuum Survey](https://research.csiro.au/racs/){ target=_blank }, centred on the location of the source.
Other surveys are available such as all epochs of the VAST Pilot Survey (including Stokes V) and other wavelength surveys such as 2MASS.

## Flux & Variability Details

Aggregate flux density statistics and variability metrics for this source, separated by flux type (peak or integrated).

## Light Curve

The light curve of the source is shown. The peak or integrated flux can be selected by using the radio selection buttons.

![!Source detail page: light curve hover panel.](../img/light-curve-hover.png){: loading=lazy align=right }

Hovering over the data points on the light curve will show an information panel that contains the date of the measurement, the flux and the measurement number.
It also contains a thumbnail image preview of the respective measurement.

## Two-epoch Node Graph

The node graph is a visual representation of what two-epoch pairings have significant variability metric values.
If an epoch pairing is significant then they are joined by a line on the graph. Hovering over the line will display the pair metrics for the selected flux type (peak or integrated) and highlight the epoch pairing on the light curve plot.

## External Search Results Table

This table shows the result of a query to the SIMBAD, NED, and TNS services for astronomical sources within 1 arcmin of the source location. Along with the name and coordinate of the matches, the on-sky separation between the source is shown along with the source type.

![!Source detail page: external search results, user assigned tags and comments.](../img/source-detail2.png){: loading=lazy }

## User Comments & Tags

Users are able to read and post comments on a source using this form, in addition to adding and removing tags, see [Source Tags and Favourites](sourcetagsfavs.md).

## JS9 Viewer Postage Stamps

[JS9 website](https://js9.si.edu){ target=_blank }.

More JS9 viewers are used to show the postage stamp FITS images of the measurements that are associated with the source, loaded from their respective image FITS files. The number of cutouts to display is configurable with the `MAX_CUTOUT_IMAGES` setting: only the first `MAX_CUTOUT_IMAGES` measurements will be displayed as cutout images. A warning will be displayed if the number of displayed cutouts has been truncated. Refer to the [pipeline configuration](../gettingstarted/configuration.md#pipeline) documentation for more information.

!!! note
    If the image data is removed from its location when the pipeline run was processed the JS9 viewer will no longer work.

![!Source detail page: postage stamps.](../img/source-detail3.png){: loading=lazy }

## Source Measurements Table

This table displays the measurements that are associated with the source. The detail page for the measurement can be reached by clicking the name of the respective measurement.

![!Source detail page: measurement and related tables.](../img/source-detail4.png){: loading=lazy }

## Related Sources Table

This table displays the sources that are a relation of the source in question. For further information refer to the [Relations](../design/association.md#relations) section in the association documentation.
