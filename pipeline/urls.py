from django.urls import include, path, re_path, register_converter
from rest_framework.routers import DefaultRouter

from . import views, converters


app_name = 'pipeline'
register_converter(converters.RightAscensionConverter, "ra")
register_converter(converters.DeclinationConverter, "dec")
register_converter(converters.AngleConverter, "angle")

router = DefaultRouter()
router.register(r'piperuns', views.RunViewSet, 'api_pipe_runs')
router.register(r'images', views.ImageViewSet, 'api_images')
router.register(r'measurements', views.MeasurementViewSet, 'api_measurements')
router.register(r'sources', views.SourceViewSet, 'api_sources')
router.register(r'rawimages', views.RawImageListSet, 'api_rawimages')
router.register(r'valruncfg', views.ValidateRunConfigSet, 'api_validateruncfg')

urlpatterns = [
    path('piperuns', views.RunIndex, name='run_index'),
    path('piperuns/<int:id>/', views.RunDetail, name='run_detail'),
    path('images', views.ImageIndex, name='image_index'),
    re_path(
        r'^images/(?P<id>\d+)(?:/(?P<action>[\w]+))?/$',
        views.ImageDetail,
        name='image_detail'
    ),
    path('measurements', views.MeasurementIndex, name='measurement_index'),
    re_path(
        r'^measurements/(?P<id>\d+)(?:/(?P<action>[\w]+))?/$',
        views.MeasurementDetail,
        name='measurement_detail'
    ),
    path('sources/query', views.SourceQuery, name='source_query'),
    re_path(
        r'^sources/(?P<id>\d+)(?:/(?P<action>[\w]+))?/$',
        views.SourceDetail,
        name='source_detail'
    ),
    path('cutout/<str:measurement_name>/', views.ImageCutout.as_view(), name='cutout'),
    path('cutout/<str:measurement_name>/<str:size>', views.ImageCutout.as_view(), name='cutout'),
    path(
        'measurements/<int:image_id>/<ra:ra_deg>,<dec:dec_deg>,<angle:radius_deg>/region',
        views.MeasurementQuery.as_view(),
        name="measurements_region"
    ),
    path('api/', include(router.urls))
]
