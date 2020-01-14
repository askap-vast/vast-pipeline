from django.urls import path, include
from django.views.generic import TemplateView
# from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import routers

from . import views


app_name = 'pipeline'

router = routers.DefaultRouter()
router.register(r'datasets', views.DatasetViewSet, 'api_datasets')

urlpatterns = [
    path('datasets', views.dataset_index, name='dataset_index'),
    path('images', TemplateView.as_view(template_name='generic_table.html'), name='image_index'),
    path('sources', TemplateView.as_view(template_name='generic_table.html'), name='source_index'),
    path('api/', include(router.urls))
]
