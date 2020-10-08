import os

from astropy.coordinates import SkyCoord, name_resolve
from astropy.coordinates.builtin_frames import frame_transform_graph
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import serializers

from vast_pipeline.utils.utils import deg2dms, deg2hms, parse_coord
from vast_pipeline.models import Image, Measurement, Run, Source, SourceFav


class RunSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField()
    n_sources = serializers.IntegerField(read_only=True)
    n_images = serializers.IntegerField(read_only=True)
    n_selavy_measurements = serializers.IntegerField(read_only=True)
    n_forced_measurements = serializers.IntegerField(read_only=True)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = Run
        fields = '__all__'
        datatables_always_serialize = ('id',)

    def get_path(self, run):
        return os.path.relpath(run.path)


class ImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    frequency = serializers.SerializerMethodField(read_only=True)

    def get_frequency(self, obj):
        return obj.band.frequency

    class Meta:
        model = Image
        fields = [
            'id',
            'name',
            'datetime',
            'frequency',
            'ra',
            'dec',
            'rms_median',
            'rms_min',
            'rms_max',
            'beam_bmaj',
            'beam_bmin',
            'beam_bpa'
        ]
        datatables_always_serialize = ('id',)


class MeasurementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    frequency = serializers.SerializerMethodField(read_only=True)

    def get_frequency(self, obj):
        return obj.image.band.frequency

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
            'island_id',
            'frequency'
        ]
        datatables_always_serialize = ('id',)


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


class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    run = RunNameSerializer()
    wavg_ra = serializers.SerializerMethodField()
    wavg_dec = serializers.SerializerMethodField()

    class Meta:
        model = Source
        exclude = ['cross_match_sources']
        datatables_always_serialize = ('id',)

    def get_wavg_ra(self, source):
        return deg2hms(source.wavg_ra, hms_format=True)

    def get_wavg_dec(self, source):
        return deg2dms(source.wavg_dec, dms_format=True)


class SourceFavSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    source = SourceNameSerializer(read_only=True)
    deletefield = serializers.SerializerMethodField()

    class Meta:
        model = SourceFav
        fields = '__all__'
        datatables_always_serialize = ('id', 'source', 'user')

    def get_deletefield(self, obj):
        redirect = reverse('vast_pipeline:api_sources_favs-detail', args=[obj.id])
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


class SesameResultSerializer(serializers.Serializer):
    object_name = serializers.CharField(required=True)
    service = serializers.ChoiceField(choices=["all", "simbad", "ned", "vizier"], required=True)
    coord = serializers.CharField(read_only=True)

    def validate(self, data):
        _ = name_resolve.sesame_database.set(data["service"])
        try:
            coord = SkyCoord.from_name(data["object_name"])
        except name_resolve.NameResolveError as e:
            raise serializers.ValidationError({"object_name": str(e)})
        data["coord"] = coord.to_string(style="hmsdms", sep=":")
        return data


class CoordinateValidatorSerializer(serializers.Serializer):
    coord = serializers.CharField(required=True)
    frame = serializers.ChoiceField(choices=frame_transform_graph.get_names(), required=True)

    def validate(self, data):
        try:
            _ = parse_coord(data["coord"], coord_frame=data["frame"])
        except ValueError as e:
            raise serializers.ValidationError({"coord": str(e.args[0])})
        return data


class ExternalSearchSerializer(serializers.Serializer):
    """Serializer for external database cone search results, i.e. SIMBAD and NED.
    """
    object_name = serializers.CharField()
    database = serializers.CharField(
        help_text="Result origin database, e.g. SIMBAD or NED."
    )
    separation_arcsec = serializers.FloatField()
    otype = serializers.CharField(help_text="Object type, e.g. QSO.")
    otype_long = serializers.CharField(
        allow_blank=True,
        help_text="Longer form of object type, e.g. quasar. Only supplied for SIMBAD results.",
    )
    ra_hms = serializers.CharField()
    dec_dms = serializers.CharField()
