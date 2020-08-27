from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from pipeline.views import Home, Login


urlpatterns = [
    path('pipe-admin/', admin.site.urls),
    path('', Home, name='index'),
    path('login/', Login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('pipeline.urls')),
    path('social-auth/', include('social_django.urls', namespace='social')),
]

# enable debug toolbar in developement
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# for production to change the base URL (e.g. server has other apps, like
# jupyter hub running)
if settings.BASE_URL and settings.BASE_URL != '':
    urlpatterns = [
        path(settings.BASE_URL.strip('/') + '/', include(urlpatterns))
    ]
