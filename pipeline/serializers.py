import os
from rest_framework import serializers

from .models import Dataset

class DatasetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    path = serializers.SerializerMethodField('get_dataset_path')

    class Meta:
        model = Dataset
        fields = '__all__'
        datatables_always_serialize = ('id',)

    def get_dataset_path(self, obj):
        return os.path.relpath(obj.path)
