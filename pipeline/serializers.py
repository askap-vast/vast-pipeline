import os
from rest_framework import serializers

from .utils.utils import deg2dms, deg2hms
from .models import Catalog, Dataset, Image, Source

class DatasetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField()
    catalogs = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = '__all__'
        datatables_always_serialize = ('id',)

    def get_path(self, dataset):
        return os.path.relpath(dataset.path)

    def get_catalogs(self, dataset):
        return dataset.catalog_set.count()

    def get_images(self, dataset):
        return dataset.image_set.count()


class ImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Image
        fields = ['id', 'name', 'time', 'ra', 'dec']
        datatables_always_serialize = ('id',)


class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Source
        fields = ['id', 'name', 'ra', 'dec', 'flux_int', 'flux_peak']
        datatables_always_serialize = ('id',)


class CatalogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    sources = serializers.SerializerMethodField()
    ave_ra = serializers.SerializerMethodField()
    ave_dec = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        exclude = ['dataset']
        datatables_always_serialize = ('id',)

    def get_sources(self, catalog):
        return catalog.source_set.count()

    def get_ave_ra(self, catalog):
        return deg2hms(catalog.ave_ra, hms_format=True)

    def get_ave_dec(self, catalog):
        return deg2dms(catalog.ave_dec, dms_format=True)
