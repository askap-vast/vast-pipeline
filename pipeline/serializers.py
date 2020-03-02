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

    class Meta:
        model = Measurement
        fields = ['id', 'name', 'ra', 'dec', 'flux_int', 'flux_peak']
        datatables_always_serialize = ('id',)


class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    measurements = serializers.IntegerField(read_only=True)
    ave_ra = serializers.SerializerMethodField()
    ave_dec = serializers.SerializerMethodField()

    class Meta:
        model = Source
        exclude = ['run', 'cross_match_sources']
        datatables_always_serialize = ('id',)

    def get_ave_ra(self, source):
        return deg2hms(source.ave_ra, hms_format=True)

    def get_ave_dec(self, source):
        return deg2dms(source.ave_dec, dms_format=True)
