# Required Data

This page gives an overview of what data is required to run the pipeline along with how to obtain the data.

## Acquiring ASKAP Data

!!! note "Note: VAST Data Releases"
    If you are a member of the VAST collaboration you will have access to the VAST data release which contains the data for the VAST Pilot Survey.
    Refer to the wiki for more details.

Data produced by the ASKAP telescope can be accessed by using [The CSIRO ASKAP Science Data Archive (CASDA)](https://research.csiro.au/casda/){:target="_blank"}.
CASDA provides a web form for users to search for the data they are interested in and request for the data to be staged for download.
Note that a form of account or registration is required to download image cube products.

All data products from CASDA should be compatible without any modifications.
Please report an [issue](https://github.com/askap-vast/vast-pipeline/issues){:target="_blank"} if you find this to not be the case.

!!! tip "Tip: CASDA Data Products"
    Descriptions of the data products available on CASDA can be found on [this page](https://research.csiro.au/casda/data-products/){:target="_blank"}.

## Pipeline Required Data

!!! warning "Warning: Correcting Data"
    Currently, the pipeline does not contain any processes to correct the data as it is ingested by the pipeline.
    For example, if corrections to the flux or positions need to be applied, these should be done to the data directly before they are processed by the pipeline.

    If an image has been previously ingested before corrections were applied, the filename of the corrected image must be changed.
    Doing so will make the pipeline see the corrected image as a new image and reingest the corrected data.

A pipeline run requires a minimum of two ASKAP observational images to process.
For each image, the following table provides a summary of the files that are required.

| Data | File Type | Description |
| ---- | --------- | ----------- |
| Primary image | .fits | The primary, Stokes I, taylor 0, image of the observation. |
| Component Catalogue | .xml, .csv, .txt | The component source catalogue produced by the source finder [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"} from the primary image. |
| Noise map of primary image | .fits | The noise (or rms) map produced by the source finder [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"} from the primary image. |
| Background map of primary image (optional) | .fits | The background (or mean) map produced by the source finder [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"} from the primary image. The background image is only required when [source monitoring](../../design/monitor) is enabled. |

Refer to the respective sections on this page for more details on these inputs.

### Image File

This is the primary image file produced by the ASKAP pipeline.
The pipeline requires the Stokes I, total intensity (taylor 0) image file.
It is also recommended to use the convolved final image, where each of the 36 individual beams have been convolved to a common resolution prior to the creation of the combined mosaic of the field.
These files are denoted by a `.conv` in the file name.

Must be in the `FITS` file format.

!!! example "Example CASDA Filename"
    ```
    image.i.SB25597.cont.taylor.0.restored.conv.fits
    ```

### Component Catalogues

Currently, the pipeline does not contain any source finding capabilities so the source catalogue must be provided.
In particular, the pipeline requires the continuum component catalogue produced by the [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"} source finder.

The files can be one of three formats:

  * `XML` The VOTable XML format of the selavy components catalogue.
    Provided by CASDA. 
    Must have a file extension of `.xml`.
  * `CSV` The csv format of the selavy components catalogue. 
    Provided by CASDA. 
    Must have a file extension of `.csv`.
  * `TXT` 'Fixed-width' formatted output produced by the selavy source finder directly. 
    These are not available through CASDA. 
    Must have a file extension of `.txt`.

!!! example "Example CASDA Filenames"
    === "xml"
        ```
        selavy-image.i.SB25597.cont.taylor.0.restored.conv.components.xml
        ```
    === "csv"
        ```
        AS107_Continuum_Component_Catalogue_25597_3792.csv
        ```
        
    Note that CASDA does not provide the fixed width text format selavy output.

!!! example "File format examples"

    === "xml"

        ``` xml
        <?xml version="1.0"?>
        <VOTABLE version="1.3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xmlns="http://www.ivoa.net/xml/VOTable/v1.3"
         xmlns:stc="http://www.ivoa.net/xml/STC/v1.30" >
          <COOSYS ID="J2000" equinox="J2000" system="eq_FK5"/>
          <RESOURCE name="Component catalogue from Selavy source finding">
            <TABLE name="Component catalogue">
              <DESCRIPTION></DESCRIPTION>
              <PARAM name="table_version" ucd="meta.version" datatype="char" arraysize="43" value="casda.continuum_component_description_v1.9"/>
              <PARAM name="imageFile" ucd="meta.file;meta.fits" datatype="char" arraysize="48" value="image.i.SB25600.cont.taylor.0.restored.conv.fits"/>
              <PARAM name="flagSubsection" ucd="meta.code" datatype="boolean" value="1"/>
              <PARAM name="subsection" ucd="" datatype="char" arraysize="25" value="[1:16449,1:14759,1:1,1:1]"/>
              <PARAM name="flagStatSec" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="StatSec" ucd="" datatype="char" arraysize="7" value="[*,*,*]"/>
              <PARAM name="searchType" ucd="meta.note" datatype="char" arraysize="7" value="spatial"/>
              <PARAM name="flagNegative" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="flagBaseline" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="flagRobustStats" ucd="meta.code" datatype="boolean" value="1"/>
              <PARAM name="flagFDR" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="threshold" ucd="phot.flux;stat.min" datatype="float" value="5"/>
              <PARAM name="flagGrowth" ucd="meta.code" datatype="boolean" value="1"/>
              <PARAM name="growthThreshold" ucd="phot.flux;stat.min" datatype="float" value="3"/>
              <PARAM name="minPix" ucd="" datatype="int" value="3"/>
              <PARAM name="minChannels" ucd="" datatype="int" value="0"/>
              <PARAM name="minVoxels" ucd="" datatype="int" value="3"/>
              <PARAM name="flagAdjacent" ucd="meta.code" datatype="boolean" value="1"/>
              <PARAM name="threshVelocity" ucd="" datatype="float" value="7"/>
              <PARAM name="flagRejectBeforeMerge" ucd="" datatype="boolean" value="0"/>
              <PARAM name="flagTwoStageMerging" ucd="" datatype="boolean" value="1"/>
              <PARAM name="pixelCentre" ucd="" datatype="char" arraysize="8" value="centroid"/>
              <PARAM name="flagSmooth" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="flagATrous" ucd="meta.code" datatype="boolean" value="0"/>
              <PARAM name="Reference frequency" ucd="em.freq;meta.main" datatype="float" unit="Hz" value="1.36749e+09"/>
              <PARAM name="thresholdActual" ucd="" datatype="float" unit="Jy/beam" value="5"/>
              <FIELD name="island_id" ID="col_island_id" ucd="meta.id.parent" datatype="char" unit="--" arraysize="20"/>
              <FIELD name="component_id" ID="col_component_id" ucd="meta.id;meta.main" datatype="char" unit="--" arraysize="24"/>
              <FIELD name="component_name" ID="col_component_name" ucd="meta.id" datatype="char" unit="" arraysize="26"/>
              <FIELD name="ra_hms_cont" ID="col_ra_hms_cont" ucd="pos.eq.ra" ref="J2000" datatype="char" unit="" arraysize="12"/>
              <FIELD name="dec_dms_cont" ID="col_dec_dms_cont" ucd="pos.eq.dec" ref="J2000" datatype="char" unit="" arraysize="13"/>
              <FIELD name="ra_deg_cont" ID="col_ra_deg_cont" ucd="pos.eq.ra;meta.main" ref="J2000" datatype="double" unit="deg" width="12" precision="6"/>
              <FIELD name="dec_deg_cont" ID="col_dec_deg_cont" ucd="pos.eq.dec;meta.main" ref="J2000" datatype="double" unit="deg" width="13" precision="6"/>
              <FIELD name="ra_err" ID="col_ra_err" ucd="stat.error;pos.eq.ra" ref="J2000" datatype="float" unit="arcsec" width="11" precision="2"/>
              <FIELD name="dec_err" ID="col_dec_err" ucd="stat.error;pos.eq.dec" ref="J2000" datatype="float" unit="arcsec" width="11" precision="2"/>
              <FIELD name="freq" ID="col_freq" ucd="em.freq" datatype="float" unit="MHz" width="11" precision="1"/>
              <FIELD name="flux_peak" ID="col_flux_peak" ucd="phot.flux.density;stat.max;em.radio;stat.fit" datatype="float" unit="mJy/beam" width="11" precision="3"/>
              <FIELD name="flux_peak_err" ID="col_flux_peak_err" ucd="stat.error;phot.flux.density;stat.max;em.radio;stat.fit" datatype="float" unit="mJy/beam" width="14" precision="3"/>
              <FIELD name="flux_int" ID="col_flux_int" ucd="phot.flux.density;em.radio;stat.fit" datatype="float" unit="mJy" width="10" precision="3"/>
              <FIELD name="flux_int_err" ID="col_flux_int_err" ucd="stat.error;phot.flux.density;em.radio;stat.fit" datatype="float" unit="mJy" width="13" precision="3"/>
              <FIELD name="maj_axis" ID="col_maj_axis" ucd="phys.angSize.smajAxis;em.radio;stat.fit" datatype="float" unit="arcsec" width="9" precision="2"/>
              <FIELD name="min_axis" ID="col_min_axis" ucd="phys.angSize.sminAxis;em.radio;stat.fit" datatype="float" unit="arcsec" width="9" precision="2"/>
              <FIELD name="pos_ang" ID="col_pos_ang" ucd="phys.angSize;pos.posAng;em.radio;stat.fit" datatype="float" unit="deg" width="8" precision="2"/>
              <FIELD name="maj_axis_err" ID="col_maj_axis_err" ucd="stat.error;phys.angSize.smajAxis;em.radio" datatype="float" unit="arcsec" width="13" precision="2"/>
              <FIELD name="min_axis_err" ID="col_min_axis_err" ucd="stat.error;phys.angSize.sminAxis;em.radio" datatype="float" unit="arcsec" width="13" precision="2"/>
              <FIELD name="pos_ang_err" ID="col_pos_ang_err" ucd="stat.error;phys.angSize;pos.posAng;em.radio" datatype="float" unit="deg" width="12" precision="2"/>
              <FIELD name="maj_axis_deconv" ID="col_maj_axis_deconv" ucd="phys.angSize.smajAxis;em.radio;askap:meta.deconvolved" datatype="float" unit="arcsec" width="18" precision="2"/>
              <FIELD name="min_axis_deconv" ID="col_min_axis_deconv" ucd="phys.angSize.sminAxis;em.radio;askap:meta.deconvolved" datatype="float" unit="arcsec" width="16" precision="2"/>
              <FIELD name="pos_ang_deconv" ID="col_pos_ang_deconv" ucd="phys.angSize;pos.posAng;em.radio;askap:meta.deconvolved" datatype="float" unit="deg" width="15" precision="2"/>
              <FIELD name="maj_axis_deconv_err" ID="col_maj_axis_deconv_err" ucd="stat.error;phys.angSize.smajAxis;em.radio;askap:meta.deconvolved" datatype="float" unit="arcsec" width="13" precision="2"/>
              <FIELD name="min_axis_deconv_err" ID="col_min_axis_deconv_err" ucd="stat.error;phys.angSize.sminAxis;em.radio;askap:meta.deconvolved" datatype="float" unit="arcsec" width="13" precision="2"/>
              <FIELD name="pos_ang_deconv_err" ID="col_pos_ang_deconv_err" ucd="stat.error;phys.angSize;pos.posAng;em.radio;askap:meta.deconvolved" datatype="float" unit="deg" width="12" precision="2"/>
              <FIELD name="chi_squared_fit" ID="col_chi_squared_fit" ucd="stat.fit.chi2" datatype="float" unit="--" width="17" precision="3"/>
              <FIELD name="rms_fit_gauss" ID="col_rms_fit_gauss" ucd="stat.stdev;stat.fit" datatype="float" unit="mJy/beam" width="15" precision="3"/>
              <FIELD name="spectral_index" ID="col_spectral_index" ucd="spect.index;em.radio" datatype="float" unit="--" width="15" precision="2"/>
              <FIELD name="spectral_curvature" ID="col_spectral_curvature" ucd="askap:spect.curvature;em.radio" datatype="float" unit="--" width="19" precision="2"/>
              <FIELD name="spectral_index_err" ID="col_spectral_index_err" ucd="stat.error;spect.index;em.radio" datatype="float" unit="--" width="15" precision="2"/>
              <FIELD name="spectral_curvature_err" ID="col_spectral_curvature_err" ucd="stat.error;askap:spect.curvature;em.radio" datatype="float" unit="--" width="19" precision="2"/>
              <FIELD name="rms_image" ID="col_rms_image" ucd="stat.stdev;phot.flux.density" datatype="float" unit="mJy/beam" width="12" precision="3"/>
              <FIELD name="has_siblings" ID="col_has_siblings" ucd="meta.code" datatype="int" unit="" width="8"/>
              <FIELD name="fit_is_estimate" ID="col_fit_is_estimate" ucd="meta.code" datatype="int" unit="" width="8"/>
              <FIELD name="spectral_index_from_TT" ID="col_spectral_index_from_TT" ucd="meta.code" datatype="int" unit="" width="8"/>
              <FIELD name="flag_c4" ID="col_flag_c4" ucd="meta.code" datatype="int" unit="" width="8"/>
              <FIELD name="comment" ID="col_comment" ucd="meta.note" datatype="char" unit="" arraysize="100"/>
              <DATA>
                <TABLEDATA>
                <TR>
                  <TD>    SB25600_island_1</TD><TD>    SB25600_component_1a</TD><TD>            J053527-691611</TD><TD>  05:35:27.9</TD><TD>    -69:16:11</TD><TD>   83.866441</TD><TD>   -69.269927</TD><TD>       0.00</TD><TD>       0.00</TD><TD>     1367.5</TD><TD>    780.068</TD><TD>         0.721</TD><TD>   843.563</TD><TD>        1.692</TD><TD>    11.80</TD><TD>     8.40</TD><TD>  176.22</TD><TD>         0.01</TD><TD>         0.01</TD><TD>        0.11</TD><TD>              3.09</TD><TD>            1.82</TD><TD>          56.44</TD><TD>         0.78</TD><TD>         2.35</TD><TD>        1.49</TD><TD>          596.911</TD><TD>       1811.003</TD><TD>          -0.93</TD><TD>             -99.00</TD><TD>           0.00</TD><TD>               0.00</TD><TD>       1.038</TD><TD>       0</TD><TD>       0</TD><TD>       1</TD><TD>       0</TD><TD>                                                                                                    </TD>
                </TR>
                <TR>
                  <TD>    SB25600_island_2</TD><TD>    SB25600_component_2a</TD><TD>            J060004-703833</TD><TD>  06:00:04.9</TD><TD>    -70:38:33</TD><TD>   90.020608</TD><TD>   -70.642664</TD><TD>       0.01</TD><TD>       0.01</TD><TD>     1367.5</TD><TD>    438.885</TD><TD>         1.202</TD><TD>   494.222</TD><TD>        2.918</TD><TD>    11.65</TD><TD>     8.86</TD><TD>    9.51</TD><TD>         0.03</TD><TD>         0.04</TD><TD>        0.40</TD><TD>              5.22</TD><TD>            0.00</TD><TD>          58.20</TD><TD>         0.09</TD><TD>         0.00</TD><TD>        0.82</TD><TD>         5351.118</TD><TD>       4419.234</TD><TD>          -1.06</TD><TD>             -99.00</TD><TD>           0.00</TD><TD>               0.00</TD><TD>       0.715</TD><TD>       1</TD><TD>       0</TD><TD>       1</TD><TD>       1</TD><TD>                                                                                                    </TD>
                </TR>
                <TR>
                  <TD>    SB25600_island_2</TD><TD>    SB25600_component_2b</TD><TD>            J060006-703854</TD><TD>  06:00:06.1</TD><TD>    -70:38:54</TD><TD>   90.025359</TD><TD>   -70.648364</TD><TD>       0.19</TD><TD>       0.24</TD><TD>     1367.5</TD><TD>     24.719</TD><TD>         1.326</TD><TD>    24.048</TD><TD>        2.986</TD><TD>    10.66</TD><TD>     8.37</TD><TD>  167.45</TD><TD>         0.59</TD><TD>         0.80</TD><TD>        9.41</TD><TD>              3.00</TD><TD>            0.00</TD><TD>         -86.64</TD><TD>         5.43</TD><TD>         0.00</TD><TD>       14.18</TD><TD>         5351.118</TD><TD>       4419.234</TD><TD>         -99.00</TD><TD>             -99.00</TD><TD>           0.00</TD><TD>               0.00</TD><TD>       0.715</TD><TD>       1</TD><TD>       0</TD><TD>       1</TD><TD>       1</TD><TD>                                                                                                    </TD>
                </TR>
                <TR>
                  <TD>    SB25600_island_3</TD><TD>    SB25600_component_3a</TD><TD>            J061931-681533</TD><TD>  06:19:31.4</TD><TD>    -68:15:33</TD><TD>   94.880875</TD><TD>   -68.259404</TD><TD>       0.49</TD><TD>       0.65</TD><TD>     1367.5</TD><TD>    258.844</TD><TD>        72.505</TD><TD>   302.138</TD><TD>       84.967</TD><TD>    11.83</TD><TD>     9.04</TD><TD>    0.90</TD><TD>         0.21</TD><TD>         0.18</TD><TD>        3.84</TD><TD>              4.77</TD><TD>            1.40</TD><TD>          63.44</TD><TD>         1.39</TD><TD>        19.02</TD><TD>        9.15</TD><TD>         1284.683</TD><TD>       2467.498</TD><TD>          -0.74</TD><TD>             -99.00</TD><TD>           0.01</TD><TD>               0.00</TD><TD>       0.277</TD><TD>       1</TD><TD>       0</TD><TD>       1</TD><TD>       0</TD><TD>                                                                                                    </TD>
                </TR>
                <TR>
                  <TD>    SB25600_island_3</TD><TD>    SB25600_component_3b</TD><TD>            J061931-681531</TD><TD>  06:19:31.0</TD><TD>    -68:15:31</TD><TD>   94.879037</TD><TD>   -68.258688</TD><TD>       0.21</TD><TD>       0.57</TD><TD>     1367.5</TD><TD>    153.160</TD><TD>        84.478</TD><TD>   157.853</TD><TD>       87.200</TD><TD>    11.40</TD><TD>     8.28</TD><TD>    6.90</TD><TD>         0.20</TD><TD>         0.21</TD><TD>        1.40</TD><TD>              4.07</TD><TD>            0.00</TD><TD>          55.21</TD><TD>         1.06</TD><TD>         0.00</TD><TD>        5.16</TD><TD>         1284.683</TD><TD>       2467.498</TD><TD>          -1.17</TD><TD>             -99.00</TD><TD>           0.02</TD><TD>               0.00</TD><TD>       0.277</TD><TD>       1</TD><TD>       0</TD><TD>       1</TD><TD>       0</TD><TD>                                                                                                    </TD>
                </TR>
                </TABLEDATA>
              </DATA>
            </TABLE>
          </RESOURCE>
        </VOTABLE>
        ```

    === "csv"

        ``` txt
        id,catalogue_id,first_sbid,other_sbids,project_id,island_id,component_id,component_name,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,ra_err,dec_err,freq,flux_peak,flux_peak_err,flux_int,flux_int_err,maj_axis,min_axis,pos_ang,maj_axis_err,min_axis_err,pos_ang_err,maj_axis_deconv,min_axis_deconv,maj_axis_deconv_err,pos_ang_deconv,min_axis_deconv_err,pos_ang_deconv_err,chi_squared_fit,rms_fit_gauss,spectral_index,spectral_index_err,spectral_curvature,spectral_curvature_err,rms_image,has_siblings,fit_is_estimate,spectral_index_from_tt,flag_c4,comment,quality_level,released_date
        20793260,3790,25600,,18,SB25600_island_2768,SB25600_component_2768a,J055644-690942,05:56:44.5,-69:09:42,89.185558,-69.161889,0.04,0.05,1367.5,0.834,0.009,0.68,0.037,9.63,7.76,165.12,0.23,0.33,3.9,0.0,0.0,0.0,-89.09,0.0,3.48,0.034,52.957,-99.0,0.0,-99.0,0.0,0.166,0,0,,0,,NOT_VALIDATED,2021-04-22T03:48:37.856Z
        20793259,3790,25600,,18,SB25600_island_2767,SB25600_component_2767a,J060047-692500,06:00:47.7,-69:25:00,90.198913,-69.416437,0.09,0.37,1367.5,0.889,0.016,2.642,0.2,29.12,9.35,2.08,2.0,0.99,1.35,26.73,4.84,0.03,2.91,6.03,1.5,1.869,234.431,-99.0,0.0,-99.0,0.0,0.175,0,0,,0,,NOT_VALIDATED,2021-04-22T03:48:37.856Z
        20793258,3790,25600,,18,SB25600_island_2766,SB25600_component_2766a,J055849-690051,05:58:49.4,-69:00:51,89.705808,-69.014253,0.14,0.24,1367.5,0.885,0.025,1.181,0.191,13.04,9.38,6.04,1.3,1.45,8.83,6.87,3.72,3.2,36.6,14.03,34.31,0.561,193.467,-99.0,0.0,-99.0,0.0,0.177,0,0,,0,,NOT_VALIDATED,2021-04-22T03:48:37.856Z
        20793257,3790,25600,,18,SB25600_island_2765,SB25600_component_2765a,J055339-683120,05:53:39.5,-68:31:20,88.414758,-68.522436,0.08,0.1,1367.5,0.906,0.014,0.895,0.063,12.78,7.08,10.0,0.43,0.43,2.33,6.37,0.0,0.54,28.11,0.0,4.65,0.138,99.302,-99.0,0.0,-99.0,0.0,0.173,0,0,,0,,NOT_VALIDATED,2021-04-22T03:48:37.856Z
        ```

    === "txt"

        ``` txt
        #           island_id            component_id component_name ra_hms_cont dec_dms_cont ra_deg_cont dec_deg_cont   ra_err  dec_err  freq  flux_peak flux_peak_err flux_int flux_int_err maj_axis min_axis pos_ang maj_axis_err min_axis_err pos_ang_err maj_axis_deconv min_axis_deconv pos_ang_deconv maj_axis_deconv_err min_axis_deconv_err pos_ang_deconv_err chi_squared_fit rms_fit_gauss spectral_index spectral_curvature spectral_index_err spectral_curvature_err  rms_image has_siblings fit_is_estimate spectral_index_from_TT flag_c4                                                                                             comment
        #                  --                      --                                               [deg]        [deg] [arcsec] [arcsec] [MHz] [mJy/beam]    [mJy/beam]    [mJy]        [mJy] [arcsec] [arcsec]   [deg]     [arcsec]     [arcsec]       [deg]        [arcsec]        [arcsec]          [deg]            [arcsec]            [arcsec]              [deg]              --    [mJy/beam]             --                 --                 --                     -- [mJy/beam]                                                                                                                                                                
          SB10342_island_1000 SB10342_component_1000a     B2337-0423  23:37:09.9    -04:23:13  354.291208    -4.387204     0.03     0.02  -0.0     15.907         0.067   19.273        0.112    17.29    13.32   86.15         0.08         0.01        0.66            7.68            2.86         -35.37                0.08                0.72               0.71          57.119       678.701          -0.79             -99.00               0.00                   0.00      0.304            0               0                      1       0                                                                                                    
          SB10342_island_1001 SB10342_component_1001a     B0001-0346  00:01:57.6    -03:46:12    0.490036    -3.770075     0.19     0.15  -0.0     12.139         0.425   24.396        0.914    24.14    15.82   61.05         0.45         0.04        2.12           17.96           10.07          50.17                0.06                0.24               4.91         690.545      1639.191          -0.58             -99.00               0.00                   0.00      0.339            1               0                      1       0                                                                                                    
          SB10342_island_1001 SB10342_component_1001b     B0001-0346  00:01:57.8    -03:46:04    0.491002    -3.767781     1.13     1.35  -0.0      4.044         0.387   10.072        1.053    50.40     9.39   42.19         3.33         0.04        0.73           48.09            0.00          40.49                0.08                0.00              31.48         690.545      1639.191          -0.36             -99.00               0.00                   0.00      0.339            1               0                      1       0                                                                                                    
          SB10342_island_1002 SB10342_component_1002a     B2333-0141  23:33:29.4    -01:41:04  353.372617    -1.684465     0.13     0.17  -0.0     14.516         0.128   47.232        0.561    35.56    17.39  140.82         0.51         0.02        0.52           33.30            7.00         -35.89                0.02                0.39               3.49         926.099      1383.267          -0.53             -99.00               0.00                   0.00      0.459            1               0                      1       0                                                                                                    
          SB10342_island_1002 SB10342_component_1002b     B2333-0141  23:33:30.8    -01:41:38  353.378227    -1.693919     0.20     0.26  -0.0      8.051         0.134   25.654        0.550    28.02    21.61  133.92         0.67         0.06        3.37           24.95           14.85         -35.94                0.05                0.13               4.34         926.099      1383.267          -0.21             -99.00               0.00                   0.00      0.459            1               0                      1       0                                                                                                    
        ```

### Noise Image File

This is the noise map that is created from the primary image file during source finding by [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"}.

Must be in the `FITS` file format.

!!! example "Example CASDA Filename"
    ```
    noiseMap.image.i.SB25600.cont.taylor.0.restored.conv.fits
    ```

### Background Image File

This is the mean map that is created from the primary image file during source finding by [`selavy`](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/index.html){:target="_blank"}.
The background image files are only required when [source monitoring](../../design/monitor) is enabled in the pipeline run.

Must be in the `FITS` file format.

!!! example "Example CASDA Filename"
    ```
    meanMap.image.i.SB25600.cont.taylor.0.restored.conv.fits
    ```

## Data Location

Data should be placed in the directories denoted by `RAW_IMAGE_DIR` and `HOME_DATA_DIR` in the pipeline configuration.
The `HOME_DATA_DIR` is designed to allow users to upload their own data to their home directory on the system where the pipeline is installed.
By default, the `HOME_DATA_DIR` is set to scan the directory called `vast-pipeline-extra-data` in the users home area.

Refer to the [Pipeline Configuration](../../gettingstarted/configuration#pipeline) section for more information.