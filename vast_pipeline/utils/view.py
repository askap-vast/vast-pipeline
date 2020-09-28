# Functions and variables used in pipeline/views.py

import logging
from vast_pipeline.models import SkyRegion
from typing import List, Dict, Optional, Any

# Defines the float format and scaling for all
# parameters presented in DATATABLES via AJAX call
FLOAT_FIELDS = {
    'ra': {
        'precision': 4,
        'scale': 1,
    },
    'ra_err': {
        'precision': 4,
        'scale': 3600.,
    },
    'uncertainty_ew': {
        'precision': 4,
        'scale': 3600.,
    },
    'dec': {
        'precision': 4,
        'scale': 1,
    },
    'dec_err': {
        'precision': 4,
        'scale': 3600,
    },
    'uncertainty_ns': {
        'precision': 4,
        'scale': 3600.,
    },
    'flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'flux_int_err': {
        'precision': 3,
        'scale': 1,
    },
    'flux_peak_err': {
        'precision': 3,
        'scale': 1,
    },
    'v_int': {
        'precision': 2,
        'scale': 1,
    },
    'eta_int': {
        'precision': 2,
        'scale': 1,
    },
    'v_peak': {
        'precision': 2,
        'scale': 1,
    },
    'eta_peak': {
        'precision': 2,
        'scale': 1,
    },
    'avg_flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'avg_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'max_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'rms_median': {
        'precision': 3,
        'scale': 1,
    },
    'rms_min': {
        'precision': 3,
        'scale': 1,
    },
    'rms_max': {
        'precision': 3,
        'scale': 1,
    },
    'new_high_sigma': {
        'precision': 3,
        'scale': 1
    },
    'compactness': {
        'precision': 3,
        'scale': 1,
    },
    'avg_compactness': {
        'precision': 2,
        'scale': 1,
    },
    'n_neighbour_dist': {
        'precision': 2,
        'scale': 60.,
    },
    'snr': {
        'precision': 2,
        'scale': 1,
    },
    'min_snr': {
        'precision': 2,
        'scale': 1,
    },
    'max_snr': {
        'precision': 2,
        'scale': 1,
    },
    'beam_bmaj': {
        'precision': 2,
        'scale': 3600.,
    },
    'beam_bmin': {
        'precision': 2,
        'scale': 3600.,
    },
    'beam_bpa': {
        'precision': 2,
        'scale': 1,
    },
}


def generate_colsfields(
    fields: List[str], url_prefix_dict: Dict[str, str],
    not_orderable_col: Optional[List[str]]=[]
) -> List[Dict[str, Any]]:
    """
    Generate data to be included in context for datatables.

    Example of url_prefix_dict format:
    api_col_dict = {
        'source.name': reverse('vast_pipeline:source_detail', args=[1])[:-2],
        'source.run.name': reverse('vast_pipeline:run_detail', args=[1])[:-2]
    }

    Args:
        fields (list): List of fields to include as columns.
        url_prefix_dict (dict): Dict containing the url prefix to form
            href links in the datatables.
        not_orderable_col (list): List of columns that should be set to
            be not orderable in the final table.

    Returns:
        colsfields (list): List containing JSON object.
    """
    colsfields = []

    for col in fields:
        field2append = {}
        if col == 'name':
            field2append = {
                'data': col, 'render': {
                    'url': {
                        'prefix': url_prefix_dict[col],
                        'col': 'name'
                    }
                }
            }
        elif '.name' in col:
            # this is for nested fields to build a render with column name
            # and id in url. The API results should look like:
            # {... , main_col : {'name': value, 'id': value, ... }}
            main_col = col.rsplit('.', 1)[0]
            field2append = {
                'data': col,
                'render': {
                    'url': {
                        'prefix': url_prefix_dict[col],
                        'col': main_col,
                        'nested': True,
                    }
                }
            }
        elif col == 'n_sibl':
            field2append = {
                'data': col, 'render': {
                    'contains_sibl': {
                        'col': col
                    }
                }
            }
        elif col in FLOAT_FIELDS:
            field2append = {
                'data': col,
                'render': {
                    'float': {
                        'col': col,
                        'precision': FLOAT_FIELDS[col]['precision'],
                        'scale': FLOAT_FIELDS[col]['scale'],
                    }
                }
            }
        else:
            field2append = {'data': col}

        if col in not_orderable_col:
            field2append['orderable'] = False

        colsfields.append(field2append)

    return colsfields


def get_skyregions_collection(run_id: Optional[int]=None) -> Dict[str, Any]:
    """
    Produce Sky region geometry shapes JSON object for d3-celestial.

    Args:
        run_id (int, optional): Run ID to filter on if not None.

    Returns:
        skyregions_collection (dict): Dictionary representing a JSON obejct
        containing the sky regions.
    """
    skyregions = SkyRegion.objects.all()
    if run_id is not None:
        skyregions = skyregions.filter(run=run_id)

    features = []

    for skr in skyregions:
        ra_fix = 360. if skr.centre_ra > 180. else 0.
        ra = skr.centre_ra - ra_fix
        dec = skr.centre_dec
        width_ra = skr.width_ra / 2.
        width_dec = skr.width_dec / 2.
        id = skr.id
        features.append(
            {
                "type": "Feature",
                "id": f"SkyRegion{id}",
                "properties": {
                    "n": f"{id:02d}",
                    "loc": [ra, dec]
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[
                        [ra+width_ra, dec+width_dec],
                        [ra+width_ra, dec-width_dec],
                        [ra-width_ra, dec-width_dec],
                        [ra-width_ra, dec+width_dec],
                        [ra+width_ra, dec+width_dec]
                    ]]
                }
            }
        )

    skyregions_collection = {
        "type": "FeatureCollection",
        "features" : features
    }

    return skyregions_collection
