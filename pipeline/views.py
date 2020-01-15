from django.shortcuts import render
from rest_framework import viewsets

from .models import Dataset
from .serializers import DatasetSerializer


# Create your views here.
def dataset_index(request):
    cols = ['id','name','path','comment']
    return render(
        request,
        'generic_table.html',
        {
            'view': 'dataset_index',
            'text': {
                'title': 'Datasets',
                'description': 'List of Datasets below',
            },
            'datatable': {
                'api': '/api/datasets/?format=datatables',
                'colsFields': [{'data': x} for x in cols],
                'colsNames': ['Id','Name','Path','Comment'],
            }
        }
    )


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
