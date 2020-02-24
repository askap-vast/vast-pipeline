import os
import shutil
from pathlib import Path
from collections import namedtuple

from django.conf import settings
from django.test import TestCase

from pipeline.pipeline.main import Pipeline


class PipelineInitTest(TestCase):

    test_folder = os.path.join(settings.PROJECT_WORKING_DIR, 'test')

    def get_create_img_folder_files(self, config):
        print('creating testing folder and files')
        if not os.path.exists(self.test_folder):
            os.makedirs(self.test_folder)

        for fname in config.IMAGE_FILES + config.SELAVY_FILES:
            full_path = os.path.join(self.test_folder, fname)
            if not os.path.exists(full_path):
                p = Path(full_path)
                p.touch()

        pass

    def cleanup_test_folder(self):
        if os.path.exists(self.test_folder):
            print('removing testing folder')
            shutil.rmtree(self.test_folder)
        pass

    def test_regex_matching_SBID(self):
        """
        test the matching of the regex patterns for selavy images and
        catalogs containing only the SBID field in their name
        """
        Config = namedtuple(
            'Config',
            'MAX_BACKWARDS_MONITOR_IMAGES IMAGE_FILES SELAVY_FILES')
        cfg = Config(
            MAX_BACKWARDS_MONITOR_IMAGES=1,
            IMAGE_FILES=[os.path.join(self.test_folder, x) for x in [
            'image.i.SB10463.cont.S190814bv.linmos.taylor.0.restored.cutout.2kpix.fits',
            'image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.fits',
            ]],
            SELAVY_FILES=[os.path.join(self.test_folder, x) for x in [
            'selavy-image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.components.txt',
            'selavy-image.i.SB10463.cont.S190814bv.linmos.taylor.0.restored.cutout.2kpix.components.txt',
            ]]
        )

        expected = {
        os.path.join(self.test_folder, 'image.i.SB10463.cont.S190814bv.linmos.taylor.0.restored.cutout.2kpix.fits'):
        os.path.join(self.test_folder, 'selavy-image.i.SB10463.cont.S190814bv.linmos.taylor.0.restored.cutout.2kpix.components.txt'),
        os.path.join(self.test_folder, 'image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.fits'):
        os.path.join(self.test_folder, 'selavy-image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.components.txt'),
        }

        # creating the folder and files for testing
        self.get_create_img_folder_files(cfg)

        pipe = Pipeline(config=cfg)

        self.assertDictEqual(pipe.img_selavy_paths, expected)

        self.cleanup_test_folder()
        pass

    def test_regex_matching_SBID_RA_DEC(self):
        """
        TBC
        """
        pass

    def test_regex_matching_SBID_RA_DEC_EPOCH(self):
        """
        TBC
        """
        pass
