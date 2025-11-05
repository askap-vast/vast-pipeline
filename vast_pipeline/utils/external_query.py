import json
from typing import Any, Dict, List
from urllib.parse import urljoin

from astropy.coordinates import SkyCoord, Angle, Longitude, Latitude
from astropy import units as u
from astroquery.simbad import Simbad
from astroquery.ipac.ned import Ned
from django.conf import settings
import requests

import logging

logger = logging.getLogger()


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
    try:
        simbad_result_table = CustomSimbad.query_region(coord, radius=radius)
    except requests.HTTPError:
        # try the Harvard mirror
        CustomSimbad.SIMBAD_URL = "https://simbad.harvard.edu/simbad/sim-script"
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
        logger.debug(r.json())
        tns_results_dict_list = r.json()["data"]
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
                logger.debug(r.json())
                object_dict = r.json()["data"]
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

def fink(coord: SkyCoord, radius: Angle) -> List[Dict[str, Any]]:
    """Perform a cone search for sources with Fink.

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
    FINK_API_URL = "https://api.fink-portal.org/api/v1/"
    search_dict = {
        'ra': str(coord.ra.deg),
        'dec': str(coord.dec.deg),
        'radius': str(radius.arcsec)
      }
    r = requests.post(
        urljoin(FINK_API_URL,'conesearch'),
        json=search_dict
    )
    
    fink_results_dict_list: List[Dict[str, Any]]
    
    print(r)
    print(r.ok)
    print(r.json())
    
    if r.ok:
        logger.debug(r.json())
        
    
        fink_results_dict_list = r.json()
        
        for result in fink_results_dict_list:
            object_coord = SkyCoord(
                    ra=result["i:ra"], dec=result["i:dec"], unit="deg"
                )
            result["otype"] = result['d:classification']
            result["otype_long"] = ""
            result['separation_arcsec'] = result['v:separation_degree']*3600.
            result["ra_hms"] = object_coord.ra.to_string(unit="hourangle")
            result["dec_dms"] = object_coord.dec.to_string(unit="deg")
            result['object_name'] = result['i:objectId']
            result['database'] = 'FINK'
            result['object_url'] = urljoin('https://fink-portal.org/',result['object_name'])
            print(result)
            
    return fink_results_dict_list


def das(
    coord: SkyCoord,
    radius: Angle,
    catalogues: List[str],
    api_url: str = "https://das.datacentral.org.au/vast",
) -> List[Dict[str, Any]]:
    """
    Performs a cone search with the DAS VAST API.

    Args:
        coord: SkyCoord of the search center.
        radius: Angle of the search radius.
        catalogues: List of catalogues to query.
        api_url: DAS API endpoint.

    Returns:
        List of dicts. Each dict contains:
            - object_name
            - database (catalogue)
            - separation_arcsec
            - ra_hms
            - dec_dms
            - object_url
            - otype (empty string, for serializer compatibility)
            - otype_long (empty string, for serializer compatibility)
    """
    results: List[Dict[str, Any]] = []

    payload = {
        "ra": coord.ra.deg,
        "dec": coord.dec.deg,
        "radius": radius.to(u.deg).value,
        "catalogues": catalogues,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            print(f"DAS API returned status: {data.get('status_msg')}")
            return results

        results_data = data.get("results", {})
        for cat in catalogues:
            cat_data = results_data.get(cat, {})
            if not cat_data:
                continue

            offsets = cat_data.get("offsets", [])
            ras = cat_data.get("ra", [])
            decs = cat_data.get("dec", [])
            ids = cat_data.get("ids", [])
            object_url_base = cat_data.get("object_url", "")

            for i in range(len(ids)):
                obj_coord = SkyCoord(ra=float(ras[i]), dec=float(decs[i]), unit="deg")
                results.append({
                    "object_name": ids[i],
                    "database": cat,
                    "separation_arcsec": float(offsets[i]) if i < len(offsets) else None,
                    "ra_hms": obj_coord.ra.to_string(unit="hourangle"),
                    "dec_dms": obj_coord.dec.to_string(unit="deg"),
                    "object_url": f"{object_url_base}{ids[i]}",
                    "otype": "",
                    "otype_long": "",
                })

    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"Error querying DAS API: {exc}")

    return results
