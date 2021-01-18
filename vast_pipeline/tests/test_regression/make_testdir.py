import os
import shutil

def make_testdir(path: str):
    '''
    Create directory for tests. If directory already exists, it deletes it first.

    Parameters
    ----------
    path : str
        path to directory
    '''
    if os.path.isdir(path):
      shutil.rmtree(path)

    os.mkdir(path)
