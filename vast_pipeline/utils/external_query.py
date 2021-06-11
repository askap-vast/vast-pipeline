from typing import Any, Dict, List

from astropy.coordinates import SkyCoord, Angle, Longitude, Latitude
from astroquery.simbad import Simbad
from astroquery.ned import Ned


def simbad(coord: SkyCoord, radius: Angle) -> List[Dict[Any, Any]]:
    CustomSimbad = Simbad()
    CustomSimbad.add_votable_fields(
        "distance_result",
        "otype(S)",
        "otype(V)",
        "otypes",
    )
    simbad_result_table = CustomSimbad.query_region(coord, radius=radius)
    if simbad_result_table is None:
        simbad_results_dict_list = []
    else:
        simbad_results_df = simbad_result_table[
            ["MAIN_ID", "DISTANCE_RESULT", "OTYPE_S", "OTYPE_V", "RA", "DEC"]
        ].to_pandas()
        simbad_results_df = simbad_results_df.rename(
            columns={
                "MAIN_ID": "object_name",
                "DISTANCE_RESULT": "separation_arcsec",
                "OTYPE_S": "otype",
                "OTYPE_V": "otype_long",
                "RA": "ra_hms",
                "DEC": "dec_dms",
            }
        )
        simbad_results_df["database"] = "SIMBAD"
        # convert coordinates to RA (hms) Dec (dms) strings
        simbad_results_df["ra_hms"] = Longitude(
            simbad_results_df["ra_hms"], unit="hourangle"
        ).to_string(unit="hourangle")
        simbad_results_df["dec_dms"] = Latitude(
            simbad_results_df["dec_dms"], unit="deg"
        ).to_string(unit="deg")
        simbad_results_dict_list = simbad_results_df.to_dict(orient="records")
    return simbad_results_dict_list


def ned(coord: SkyCoord, radius: Angle) -> List[Dict[Any, Any]]:
    ned_result_table = Ned.query_region(coord, radius=radius)
    if ned_result_table is None or len(ned_result_table) == 0:
        ned_results_dict_list = []
    else:
        ned_results_df = ned_result_table[
            ["Object Name", "Separation", "Type", "RA", "DEC"]
        ].to_pandas()
        ned_results_df = ned_results_df.rename(
            columns={
                "Object Name": "object_name",
                "Separation": "separation_arcsec",
                "Type": "otype",
                "RA": "ra_hms",
                "DEC": "dec_dms",
            }
        )
        ned_results_df["otype_long"] = ""  # NED does not supply verbose object types
        # convert NED result separation (arcmin) to arcsec
        ned_results_df["separation_arcsec"] = ned_results_df["separation_arcsec"] * 60
        # convert coordinates to RA (hms) Dec (dms) strings
        ned_results_df["ra_hms"] = Longitude(
            ned_results_df["ra_hms"], unit="deg"
        ).to_string(unit="hourangle")
        ned_results_df["dec_dms"] = Latitude(
            ned_results_df["dec_dms"], unit="deg"
        ).to_string(unit="deg")
        ned_results_df["database"] = "NED"
        # convert dataframe to dict and replace float NaNs with None for JSON encoding
        ned_results_dict_list = ned_results_df.sort_values("separation_arcsec").to_dict(
            orient="records"
        )
    return ned_results_dict_list
