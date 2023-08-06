import os
from collections import defaultdict
from typing import Any, Dict, List

from django.conf import settings as s

from vast_pipeline.pipeline.config import PipelineConfig, make_config_template


data_path = './vast_pipeline/tests/regression-data'


def gen_obs_list(epochs: List[str]) -> List[str]:
    '''
    Generate list of observations.

    Parameters
    ----------
    epochs : List[str]
        The epochs to include in the list.

    Returns
    -------
    obs : List[str]
        The list of observations.
    '''
    obs = []
    for epoch in epochs:
        # -06A
        obs.append(
            os.path.join('EPOCH' + epoch, 'VAST_2118-06A.EPOCH' + epoch)
        )
        # +00A
        if epoch not in ['12']:
            obs.append(
                os.path.join('EPOCH' + epoch, 'VAST_2118+00A.EPOCH' + epoch)
            )
        # 0127
        if epoch not in ['03x', '02', '12']:
            obs.append(
                os.path.join('EPOCH' + epoch, 'VAST_0127-73A.EPOCH' + epoch)
            )
    return obs


def obs_list(obs: List[str], file_type: str) -> List[str]:
    '''
    Generate observation list with the file extension.

    Parameters
    ----------
    obs : List[str]
        The list of observations (prefix).
    file_type : str
        The file extension to append to obs.

    Returns
    -------
    obs_files : List[str]
        The list of observations with file extensions.
    '''
    obs_files = [
        os.path.join(data_path, o + file_type) for o in obs
    ]
    return obs_files


def list_to_dict(obs: List[str]) -> Dict[str, List[str]]:
    '''
    Convert from list of observations to dictionary.

    Parameters
    ----------
    obs : List[str]
        List of observations.

    Returns
    -------
    obs_dict : Dict[str, str]
        Dictionary of observations.
    '''
    obs_dict = defaultdict(list)
    for o in obs:
        _, field = os.path.split(o)
        epoch = field.split('.')[1]
        obs_dict[epoch[5:]].append(o)

    # Needs to have epoch keys that are sortable
    obs_dict = {f"epoch{e:02d}": obs_dict[val] for e, val in enumerate(obs_dict.keys())}

    return obs_dict


def obs_dict(obs: Dict[str, str], file_type: str) -> Dict[str, List[str]]:
    '''
    Generate observation dictionary with the file extension.

    Parameters
    ----------
    obs : dict
        The dictionary of observations (prefix).
    file_type : str
        The file extension to append to obs.

    Returns
    -------
    obs_files : Dict[str, List[str]]
        The dictionary of observations with file extensions.
    '''
    obs_files: Dict[str, List[str]] = {}
    for epoch in obs.keys():
        obs_files[epoch] = []
        for image in obs[epoch]:
            obs_files[epoch].append(os.path.join(data_path, image + file_type))
    return obs_files


def gen_config(folder: str, run_path: str, epochs: List[str]):
    '''
    Generate the config file.

    Parameters
    ----------
    folder : str
        The test folder name.
    run_path : str
        The path to the test folder.
    epochs : List[str]
        The epochs to include in observations.
    '''
    path = os.path.join(run_path, folder)
    modes = folder.split('-')

    # change config settings
    settings = dict(s.PIPE_RUN_CONFIG_DEFAULTS)
    settings["run_path"] = path
    # add config file paths
    obs = gen_obs_list(epochs)
    obs_func: Any = obs_list
    if 'epoch' in modes:
        obs: Dict[str, List[str]] = list_to_dict(obs)  # type: ignore[no-redef]
        obs_func = obs_dict
        settings['epoch_mode'] = True

    settings['image_files'] = obs_func(obs, '.I.cutout.fits')
    settings['selavy_files'] = obs_func(obs, '.I.cutout.components.txt')
    settings['noise_files'] = obs_func(obs, '.I.cutout_rms.fits')
    settings['background_files'] = obs_func(obs, '.I.cutout_bkg.fits')
    # other config keys
    if 'basic' in modes:
        settings['association_method'] = 'basic'
    elif 'advanced' in modes:
        settings['association_method'] = 'advanced'
    elif 'deruiter' in modes:
        settings['association_method'] = 'deruiter'
    if 'forced' in modes:
        settings['monitor'] = True
    if 'parallel' in modes:
        settings['association_parallel'] = True

    # write config file
    config_str = make_config_template(PipelineConfig.TEMPLATE_PATH, **settings)
    with open(os.path.join(path, 'config.yaml'), 'w') as fp:
        fp.write(config_str)
