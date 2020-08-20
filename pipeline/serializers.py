import os

from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import serializers

from .utils.utils import deg2dms, deg2hms
from .models import Image, Measurement, Run, Source, SourceFav


class RunSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField()
    n_sources = serializers.IntegerField(read_only=True)
    n_images = serializers.IntegerField(read_only=True)
    status = serializers.CharField(source='get_status_display')

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
        fields = [
            'id',
            'name',
            'datetime',
            'ra',
            'dec',
            'rms_median',
            'rms_min',
            'rms_max'
        ]
        datatables_always_serialize = ('id',)


class MeasurementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Measurement
        fields = [
            'id',
            'name',
            'ra',
            'ra_err',
            'uncertainty_ew',
            'dec',
            'dec_err',
            'uncertainty_ns',
            'flux_int',
            'flux_int_err',
            'flux_peak',
            'flux_peak_err',
            'compactness',
            'snr',
            'has_siblings',
            'forced',
        ]
        datatables_always_serialize = ('id',)


class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    measurements = serializers.IntegerField(read_only=True)
    selavy_measurements = serializers.IntegerField(read_only=True)
    forced_measurements = serializers.IntegerField(read_only=True)
    relations = serializers.IntegerField(read_only=True)
    siblings_count = serializers.IntegerField(read_only=True)
    contains_siblings = serializers.BooleanField(read_only=True)
    wavg_ra = serializers.SerializerMethodField()
    wavg_dec = serializers.SerializerMethodField()

    class Meta:
        model = Source
        exclude = ['run', 'cross_match_sources']
        datatables_always_serialize = ('id',)

    def get_wavg_ra(self, source):
        return deg2hms(source.wavg_ra, hms_format=True)

    def get_wavg_dec(self, source):
        return deg2dms(source.wavg_dec, dms_format=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =['username']


class RunNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Run
        fields = ['id', 'name']
        datatables_always_serialize = ('id',)


class SourceNameSerializer(serializers.ModelSerializer):
    run = RunNameSerializer()
    class Meta:
        model = Source
        fields= ['id', 'name', 'run']
        datatables_always_serialize = ('id',)


class SourceFavSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    source = SourceNameSerializer(read_only=True)
    deletefield = serializers.SerializerMethodField()

    class Meta:
        model = SourceFav
        fields = '__all__'
        datatables_always_serialize = ('id', 'source', 'user')

    def get_deletefield(self, obj):
        redirect = reverse('pipeline:api_sources_favs-detail', args=[obj.id])
        string = (
            f'<a href="{redirect}" class="text-danger" onclick="sendDelete(event)">'
            '<i class="fas fa-trash"></i></a>'
        )
        return string


class RawImageSelavyObjSerializer(serializers.Serializer):
    path = serializers.CharField()
    title = serializers.CharField()
    datatokens = serializers.CharField()


class RawImageSelavyListSerializer(serializers.Serializer):
    fits = RawImageSelavyObjSerializer(many=True)
    selavy = RawImageSelavyObjSerializer(many=True)
