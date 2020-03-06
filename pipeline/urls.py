from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from . import views


app_name = 'pipeline'

router = DefaultRouter()
router.register(r'piperuns', views.RunViewSet, 'api_pipe_runs')
router.register(r'images', views.ImageViewSet, 'api_images')
router.register(r'measurements', views.MeasurementViewSet, 'api_measurements')
router.register(r'sources', views.SourceViewSet, 'api_sources')

urlpatterns = [
    path('piperuns', views.RunIndex, name='run_index'),
    path('piperuns/<int:id>/', views.RunDetail, name='run_detail'),
    path('images', views.ImageIndex, name='image_index'),
    path('measurements', views.MeasurementIndex, name='measurement_index'),
    path('sources/overview', views.SourceIndex, name='source_index'),
    path('sources/query', views.SourceQuery, name='source_query'),
    re_path(
        r'^sources/(?P<id>\d+)(?:/(?P<action>[\w]+))?/$',
        views.SourceDetail,
        name='source_detail'
    ),
    path('cutout/<str:measurement_name>/', views.ImageCutout.as_view(), name='cutout'),
    path('api/', include(router.urls))
]
