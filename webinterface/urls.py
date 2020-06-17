from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView
from pipeline.views import Home, Login


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', Home, name='index'),
    path('login/', Login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('pipeline.urls')),
    path('social-auth/', include('social_django.urls', namespace='social')),
]
