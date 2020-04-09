import os
from rest_framework import serializers

from .utils.utils import deg2dms, deg2hms
from .models import Image, Measurement, Run, Source


class RunSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField()
    n_sources = serializers.IntegerField(read_only=True)
    n_images = serializers.IntegerField(read_only=True)

    class Meta:
        model = Run
        fields = '__all__'
        datatables_always_serialize = ('id',)

    def get_path(self, run):
        return os.path.relpath(run.path)


class ImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Image
        fields = ['id', 'name', 'datetime', 'ra', 'dec']
        datatables_always_serialize = ('id',)


class MeasurementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    ra = serializers.SerializerMethodField()
    ra_err = serializers.SerializerMethodField()
    dec = serializers.SerializerMethodField()
    dec_err = serializers.SerializerMethodField()

    class Meta:
        model = Measurement
        fields = ['id', 'name', 'ra', 'ra_err', 'dec', 'dec_err', 'flux_int', 'flux_peak']
        datatables_always_serialize = ('id',)

    def get_ra(self, measurement):
        return "{:.4f}".format(measurement.ra)

    def get_ra_err(self, measurement):
        return "{:.5f}".format(measurement.ra_err)

    def get_dec(self, measurement):
        return "{:.4f}".format(measurement.dec)

    def get_dec_err(self, measurement):
        return "{:.5f}".format(measurement.dec_err)


class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    measurements = serializers.IntegerField(read_only=True)
    wavg_ra = serializers.SerializerMethodField()
    wavg_dec = serializers.SerializerMethodField()
    v_int = serializers.SerializerMethodField()
    v_peak = serializers.SerializerMethodField()
    eta_int = serializers.SerializerMethodField()
    eta_peak = serializers.SerializerMethodField()
    avg_flux_int = serializers.SerializerMethodField()
    avg_flux_peak = serializers.SerializerMethodField()
    max_flux_peak = serializers.SerializerMethodField()

    class Meta:
        model = Source
        exclude = ['run', 'cross_match_sources']
        datatables_always_serialize = ('id',)

    def get_wavg_ra(self, source):
        return deg2hms(source.wavg_ra, hms_format=True)

    def get_wavg_dec(self, source):
        return deg2dms(source.wavg_dec, dms_format=True)

    def get_v_int(self, source):
        return round(source.v_int, 2)

    def get_eta_int(self, source):
        return round(source.v_int, 2)

    def get_v_peak(self, source):
        return round(source.v_int, 2)

    def get_eta_peak(self, source):
        return round(source.v_int, 2)

    def get_avg_flux_int(self, source):
        return round(source.avg_flux_int, 3)

    def get_avg_flux_peak(self, source):
        return round(source.avg_flux_peak, 3)

    def get_max_flux_peak(self, source):
        return round(source.max_flux_peak, 3)
