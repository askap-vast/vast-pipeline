import json
from typing import Any, Dict, List
from urllib.parse import urljoin

from astropy.coordinates import SkyCoord, Angle, Longitude, Latitude
from astroquery.simbad import Simbad
from astroquery.ned import Ned
from django.conf import settings
import requests


def simbad(coord: SkyCoord, radius: Angle) -> List[Dict[str, Any]]:
    """Perform a cone search for sources with SIMBAD.

    Args:
        coord: The coordinate of the centre of the cone.
        radius: The radius of the cone in angular units.

    Returns:
        A list of dicts, where each dict is a query result row with the following keys:

        - object_name: the name of the astronomical object.
        - database: the source of the result, i.e. SIMBAD.
        - separation_arcsec: separation to the query coordinate in arcsec.
        - otype: object type.
        - otype_long: long form of the object type.
        - ra_hms: RA coordinate string in hms format.
        - dec_dms: Dec coordinate string in ±dms format.
    """
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


def ned(coord: SkyCoord, radius: Angle) -> List[Dict[str, Any]]:
    """Perform a cone search for sources with NED.

    Args:
        coord: The coordinate of the centre of the cone.
        radius: The radius of the cone in angular units.

    Returns:
        A list of dicts, where each dict is a query result row with the following keys:

        - object_name: the name of the astronomical object.
        - database: the source of the result, i.e. NED.
        - separation_arcsec: separation to the query coordinate in arcsec.
        - otype: object type.
        - otype_long: long form of the object type.
        - ra_hms: RA coordinate string in hms format.
        - dec_dms: Dec coordinate string in ±dms format.
    """
    # NED API doesn't supply the long-form object types.
    # Copied from https://ned.ipac.caltech.edu/Documents/Guides/Database
    NED_OTYPES = {
        "*": "Star or Point Source",
        "**": "Double star",
        "*Ass": "Stellar association",
        "*Cl": "Star cluster",
        "AbLS": "Absorption line system",
        "Blue*": "Blue star",
        "C*": "Carbon star",
        "EmLS": "Emission line source",
        "EmObj": "Emission object",
        "exG*": "Extragalactic star (not a member of an identified galaxy)",
        "Flare*": "Flare star",
        "G": "Galaxy",
        "GammaS": "Gamma ray source",
        "GClstr": "Cluster of galaxies",
        "GGroup": "Group of galaxies",
        "GPair": "Galaxy pair",
        "GTrpl": "Galaxy triple",
        "G_Lens": "Lensed image of a galaxy",
        "HII": "HII region",
        "IrS": "Infrared source",
        "MCld": "Molecular cloud",
        "Neb": "Nebula",
        "Nova": "Nova",
        "Other": "Other classification (e.g. comet; plate defect)",
        "PN": "Planetary nebula",
        "PofG": "Part of galaxy",
        "Psr": "Pulsar",
        "QGroup": "Group of QSOs",
        "QSO": "Quasi-stellar object",
        "Q_Lens": "Lensed image of a QSO",
        "RadioS": "Radio source",
        "Red*": "Red star",
        "RfN": "Reflection nebula",
        "SN": "Supernova",
        "SNR": "Supernova remnant",
        "UvES": "Ultraviolet excess source",
        "UvS": "Ultraviolet source",
        "V*": "Variable star",
        "VisS": "Visual source",
        "WD*": "White dwarf",
        "WR*": "Wolf-Rayet star",
        "XrayS": "X-ray source",
        "!*": "Galactic star",
        "!**": "Galactic double star",
        "!*Ass": "Galactic star association",
        "!*Cl": "Galactic Star cluster",
        "!Blue*": "Galactic blue star",
        "!C*": "Galactic carbon star",
        "!EmObj": "Galactic emission line object",
        "!Flar*": "Galactic flare star",
        "!HII": "Galactic HII region",
        "!MCld": "Galactic molecular cloud",
        "!Neb": "Galactic nebula",
        "!Nova": "Galactic nova",
        "!PN": "Galactic planetary nebula",
        "!Psr": "Galactic pulsar",
        "!RfN": "Galactic reflection nebula",
        "!Red*": "Galactic red star",
        "!SN": "Galactic supernova",
        "!SNR": "Galactic supernova remnant",
        "!V*": "Galactic variable star",
        "!WD*": "Galactic white dwarf",
        "!WR*": "Galactic Wolf-Rayet star",
    }
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
        ned_results_df["otype_long"] = ned_results_df.otype.replace(NED_OTYPES)
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


def tns(coord: SkyCoord, radius: Angle) -> List[Dict[str, Any]]:
    """Perform a cone search for sources with the Transient Name Server (TNS).

    Args:
        coord: The coordinate of the centre of the cone.
        radius: The radius of the cone in angular units.

    Returns:
        A list of dicts, where each dict is a query result row with the following keys:

        - object_name: the name of the transient.
        - database: the source of the result, i.e. TNS.
        - separation_arcsec: separation to the query coordinate in arcsec.
        - otype: object type.
        - otype_long: long form of the object type. Not given by TNS, will always be
            an empty string.
        - ra_hms: RA coordinate string in hms format.
        - dec_dms: Dec coordinate string in ±dms format.
    """
    TNS_API_URL = "https://www.wis-tns.org/api/"
    headers = {
        "user-agent": settings.TNS_USER_AGENT,
    }

    search_dict = {
        "ra": coord.ra.to_string(unit="hourangle", sep=":", pad=True),
        "dec": coord.dec.to_string(unit="deg", sep=":", alwayssign=True, pad=True),
        "radius": str(radius.value),
        "units": radius.unit.name,
    }
    r = requests.post(
        urljoin(TNS_API_URL, "get/search"),
        data={"api_key": settings.TNS_API_KEY, "data": json.dumps(search_dict)},
        headers=headers,
    )
    tns_results_dict_list: List[Dict[str, Any]]
    if r.ok:
        tns_results_dict_list = r.json()["data"]["reply"]
        # Get details for each object result. TNS API doesn't support doing this in one
        # request, so we iterate.
        for result in tns_results_dict_list:
            search_dict = {
                "objname": result["objname"],
            }
            r = requests.post(
                urljoin(TNS_API_URL, "get/object"),
                data={"api_key": settings.TNS_API_KEY, "data": json.dumps(search_dict)},
                headers=headers,
            )
            if r.ok:
                object_dict = r.json()["data"]["reply"]
                object_coord = SkyCoord(
                    ra=object_dict["radeg"], dec=object_dict["decdeg"], unit="deg"
                )
                result["otype"] = object_dict["object_type"]["name"]
                if result["otype"] is None:
                    result["otype"] = ""
                result["otype_long"] = ""
                result["separation_arcsec"] = coord.separation(object_coord).arcsec
                result["ra_hms"] = object_coord.ra.to_string(unit="hourangle")
                result["dec_dms"] = object_coord.dec.to_string(unit="deg")
                result["database"] = "TNS"
                result["object_name"] = object_dict["objname"]
    return tns_results_dict_list
