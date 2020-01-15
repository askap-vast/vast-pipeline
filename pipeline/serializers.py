import os
from rest_framework import serializers

from .models import Dataset, Image, Source

class DatasetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField('get_dataset_path')

    class Meta:
        model = Dataset
        fields = '__all__'
        datatables_always_serialize = ('id',)

    def get_dataset_path(self, obj):
        return os.path.relpath(obj.path)


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
