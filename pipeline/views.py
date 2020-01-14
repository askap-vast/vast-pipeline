from django.shortcuts import render
from rest_framework import viewsets

from .models import Dataset
from .serializers import DatasetSerializer


# Create your views here.
def dataset_index(request):
    return render(request, 'generic_table.html')


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
