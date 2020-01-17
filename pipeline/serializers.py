import os
from rest_framework import serializers

from .models import Dataset, Image, Source

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
