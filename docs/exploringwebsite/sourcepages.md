# Source Pages

This page details the website pages for information on the sources.

## Source Query

Users can filter and query the sources currently in the database by using the form located on this page. 

The form is submitted by clicking the blue :fontawesome-solid-search: button, the red :fontawesome-solid-trash: button  will reset the form by removing all entered values.
Once the form is submitted the results are dynamically updated in the results table below the form (i.e. on the same page).

The following sections provide further details on the form.

![!The source query form.](../img/source-query-form.png){: loading=lazy }

### Data Source

Here a specific pipeline run can be selected from a dropdown list to filter sources to only those from the chosen run. By default sources from all runs are shown.

!!! note
    Only successfully completed pipeline runs are available to select. This rule also applies when `all` is selected.

### Cone Search

Users can choose whether to input their coordinates directly or use the object name resolver to attempt to fetch the coordinates.

#### Manual Input

The format of the coordinates should be in a standard format that is recognised by astropy, for example:

* `21 29 45.29 -04 29 11.9`
* `21:29:45.29 -04:29:11.9`
* `322.4387083 -4.4866389`

Galactic coordinates can also be entered by selecting `Galactic` from the dropdown menu that is set to `ICRS` by default. 
Feedback will be given immediately whether the coordinates are valid, as shown in the screenshots below:

![!Cone search: accepted coordinate input.](../img/cone-search-ok.png){: loading=lazy }
![!Cone search: rejected coordinate input.](../img/cone-search-bad.png){: loading=lazy }

Once the coordinates have been entered the radius value must also be specified as shown in the screenshot above. Use the dropdown menu to change the radius unit to be `arcsec`, `arcmin` or `deg`.

#### Name Resolver

To use the name resolver, the name of the source should be entered into the `Object Name` field (e.g. `PSR J2129-04`), select the name resolver service and then click the `Resolve` button.
The coordinates will then be automatically filled on a successful match.

![!Cone search: successful name resolver.](../img/cone-search-resolve.png){: loading=lazy }

if no match is found then this will be communicated by the form as below:

![!Cone search: unsuccessful name resolver.](../img/cone-search-resolver-bad.png){: loading=lazy }

### Table Filters

This section of the form allows the user to place thresholds and selections on specific metrics of the sources. 
Please refer to the [Source Statistics page](../design/sourcestats.md) for details on the different metrics. There are also tooltips located on the form to offer explanations.

The following options are not standard source metrics:

#### Include and Exclude Tags

Users can attach tags to sources (see [Source Tags and Favourites](sourcetagsfavs.md)) and here tags can be selected to include or exclude in the source search.

#### Source Selection

Here specific sources can be searched for by entering the source names, or source database `id` values, in a comma-separated list. For example:

* `ASKAP_011816.05-730747.77,ASKAP_011816.05-730747.77,ASKAP_213221.21-040900.42`
* `1031,1280,52`

are valid entries to this search field. Use the dropdown menu to declare whether `name` (default) or `id` values are being searched.

### Results Table

Located directly below the form is the results table which is dynamically updated once the form is submitted.
The full detail page of a specific source can be accessed by clicking on the source name in the table. 
Explanation of the table options can be found in the [DataTables section](datatables.md).

![!Source query results table.](../img/source-query-results.png){: loading=lazy }

## Source Detail Page

This page presents all the information about the selected source, including a light curve and cutouts of all the measurements that are associated to the source.

![!Source detail page.](../img/source-detail1.png){: loading=lazy }

### Star, SIMBAD, NED, Previous & Next Buttons

These buttons do the following:

* **Star**: Adds the source to the user's favourites, see [Source Tags and Favourites](sourcetagsfavs.md).
* **SIMBAD**: Performs a cone search on SIMBAD with a radius of 10 arcmin centered on the source location.
* **NED**: Performs a cone search on NED with a radius of 10 arcmin centered on the source location.
* **Previous**: Navigates to the previous source that was returned in the source query.
* **Next**: Navigates to the next source that was returned in the source query

### Details

A text representation of details of the measurement.

### User Comments & Tags

Users are able to read and post comments on a measurement using this form, in addition to adding and removing tags, see [Source Tags and Favourites](sourcetagsfavs.md).

### Aladin Lite Viewer

[Aladin Lite Documentation](https://aladin.u-strasbg.fr/AladinLite/doc/){ target=_blank }.

The central panel contains an Aladin Lite viewer, which by default displays the HIPS image from the [Rapid ASKAP Continuum Survey](https://research.csiro.au/racs/){ target=_blank }, centred on the location of the source.
Other surveys are available such as all epochs of the VAST Pilot Survey (including Stokes V) and other wavelength surveys such as 2MASS.

### Light Curve

The light curve of the source is shown. The peak or integrated flux can be selected by using the radio selection buttons.

![!Source detail page: light curve, node graph and external search results.](../img/source-detail2.png){: loading=lazy }

### Two-epoch Node Graph

The node graph is a visual representation of what two-epoch pairings have significant variability metric values. 
If an epoch pairing is significant then they are joined by a line on the graph. Hovering over the line will highlight the epoch pairing on the light curve plot.

### External Search Results Table

This table shows the result of a query to the SIMBAD and NED services for astronomical sources within 1 arcmin of the source location. 
Along with the name and coordinate of the matches, the on-sky separation between the source is shown along with the source type.

### JS9 Viewer Postage Stamps

[JS9 website](https://js9.si.edu){ target=_blank }.

The JS9 viewer is used to show the postage stamp FITS images of the measurements that are associated with the source, loaded from their respective image FITS files.

!!! note
    If the image data is removed from its location when the pipeline run was processed the JS9 viewer will no longer work.

![!Source detail page: postage stamps.](../img/source-detail3.png){: loading=lazy }

### Source Measurements Table

This table displays the measurements that are associated with the source. The detail page for the measurement can be reached by clicking the name of the respective measurement.

![!Source detail page: measurement and related tables.](../img/source-detail4.png){: loading=lazy }

### Related Sources Table

This table displays the sources that are a relation of the source in question. For further information refer to the [Relations](../design/association.md#relations) section in the association documentation.
