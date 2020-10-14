import os
import pandas as pd

from django.test import SimpleTestCase
from django.conf import settings as s

from rest_framework.renderers import JSONRenderer

import vast_pipeline.serializers as ser
import vast_pipeline.models as mod


class SerializerTest(SimpleTestCase):
    """
    testing serializers
    """

    @staticmethod
    def create_run_obj():
        run_name = 'my_test_pipe_run'
        obj = mod.Run(
            name=run_name,
            path=os.path.join(s.PIPELINE_WORKING_DIR, run_name),
            description=f'this is the description of my {run_name}'
        )
        return obj

    def test_run_serializer(self):
        """
        testing Run model serializer
        """
        expected_data = {
            'id': None,
            'path': 'testing-projects/my_test_pipe_run',
            'name': 'my_test_pipe_run',
            'description': 'this is the description of my my_test_pipe_run'
        }
        expected_content = (
            b'{"id":null,"path":"testing-projects/my_test_pipe_run","name":"my_test_pipe_run",'
            b'"description":"this is the description of my my_test_pipe_run"}'
        )

        run = self.create_run_obj()
        serializer = ser.RunSerializer(run)
        ser_data = serializer.data
        ser_data.pop('time')
        self.assertDictEqual(ser_data, expected_data, msg='data not matching')
        content = JSONRenderer().render(ser_data)
        self.assertEqual(content, expected_content, msg='data not matching')

    @staticmethod
    def create_skyreg_obj():
        obj = mod.SkyRegion(
            centre_ra=13.57935,
            centre_dec=-24.88039,
            xtr_radius=1414.21356,
            x=0.88182,
            y=0.21300,
            z=-0.42072,
        )
        return obj

    @staticmethod
    def create_band_obj():
        obj = mod.Band(
            name='943',
            frequency=943,
            bandwidth=0,
        )
        return obj

    def create_image_obj(self):
        image_name = 'image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.fits'
        time = pd.Timestamp('2020-01-01 01:01:01', tz='UTC')
        skyreg = self.create_skyreg_obj()
        band = self.create_band_obj()

        obj = mod.Image(
            band=band,
            skyreg=skyreg,
            measurements_path=os.path.join(
                s.PIPELINE_WORKING_DIR,
                f'SB9602_{time.isoformat()}',
                'measurements.parquet'
                ),
            polarisation='I',
            name=image_name,
            path=os.path.join(s.PIPELINE_WORKING_DIR, 'images' , image_name),
            datetime=time,
            jd=time.to_julian_date(),
            duration=38290.3,
            ra=13.57935,
            dec=-24.88039,
            fov_bmaj=0.78567,
            fov_bmin=0.78567,
            radius_pixels=1414.21356,
            beam_bmaj=0.00343,
            beam_bmin=0.00277,
            beam_bpa=81.58025,
        )
        return obj

    def test_image_serializer(self):
        """
        testing Image model serializer
        """
        expected_data = {
            'id': None,
            'name': 'image.i.SB9602.cont.taylor.0.restored.cutout.2kpix.fits',
            'datetime': '2020-01-01T01:01:01Z',
            'ra': 13.57935,
            'dec': -24.88039,
        }
        expected_content = (
            b'{"id":null,"name":"image.i.SB9602.cont.taylor.0.restored.'
            b'cutout.2kpix.fits","datetime":"2020-01-01T01:01:01Z","ra":'
            b'13.57935,"dec":-24.88039}'
        )

        img = self.create_image_obj()
        serializer = ser.ImageSerializer(img)
        self.assertDictEqual(
            serializer.data,
            expected_data,
            msg='data not matching'
        )
        content = JSONRenderer().render(serializer.data)
        self.assertEqual(content, expected_content, msg='data not matching')

    @staticmethod
    def create_meas_obj():
        obj = mod.Measurement(
            name='SB9602_component_933a',
            ra=12.964284,
            ra_err=0.03,
            dec=-24.590021,
            dec_err=0.03,
            bmaj=15.36,
            err_bmaj=0.25,
            bmin=10.65,
            err_bmin=0.03,
            pa=65.45,
            err_pa=1.66,
            flux_int=0.237,
            flux_int_err=0.003,
            flux_peak=0.179,
            flux_peak_err=0.001,
            chi_squared_fit=0.004,
            spectral_index=-99.0,
            spectral_index_from_TT=True,
            component_id='component_933a',
            island_id='island_933',
        )
        return obj

    def test_measurement_serializer(self):
        """
        testing Measurement model serializer
        """
        expected_data = {
            'id': None,
            'name': 'SB9602_component_933a',
            'ra': 12.964284,
            'dec': -24.590021,
            'flux_int': 0.237,
            'flux_peak': 0.179
        }
        expected_content = (
            b'{"id":null,"name":"SB9602_component_933a","ra":12.964284,'
            b'"dec":-24.590021,"flux_int":0.237,"flux_peak":0.179}'
        )

        meas = self.create_meas_obj()
        serializer = ser.MeasurementSerializer(meas)
        self.assertDictEqual(
            serializer.data,
            expected_data,
            msg='data not matching'
        )
        content = JSONRenderer().render(serializer.data)
        self.assertEqual(content, expected_content, msg='data not matching')

    @staticmethod
    def create_source_obj():
        obj = mod.Source(
            name='src_00:56:29.78-24:24:59.05',
            ave_ra=14.124,
            ave_dec=-24.416,
            ave_flux_int=0.24,
            ave_flux_peak=0.21475,
            max_flux_peak=0.252,
            v_int=0.119,
            v_peak=0.165,
            eta_int=209.215,
            eta_peak=1258.25,
        )
        return obj

    def test_source_serializer(self):
        """
        testing Source model serializer
        """
        expected_data = {
        'id': None,
            'ave_ra': '00h56m29.76s',
            'ave_dec': '-24d24m57.60s',
            'name': 'src_00:56:29.78-24:24:59.05',
            'new': False,
            'ave_flux_int': 0.24,
            'ave_flux_peak': 0.21475,
            'max_flux_peak': 0.252,
            'v_int': 0.119,
            'v_peak': 0.165,
            'eta_int': 209.215,
            'eta_peak': 1258.25
        }
        expected_content = (
            b'{"id":null,"ave_ra":"00h56m29.76s","ave_dec":"-24d24m57.60s"'
            b',"name":"src_00:56:29.78-24:24:59.05","new":false,"ave_flux_int":0.24,'
            b'"ave_flux_peak":0.21475,"max_flux_peak":0.252,"v_int":0.119,"v_peak":0.165,'
            b'"eta_int":209.215,"eta_peak":1258.25}')

        src = self.create_source_obj()
        serializer = ser.SourceSerializer(src)
        self.assertDictEqual(
            serializer.data,
            expected_data,
            msg='data not matching'
        )
        content = JSONRenderer().render(serializer.data)
        self.assertEqual(content, expected_content, msg='data not matching')
