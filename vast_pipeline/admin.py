"""
This module contains the admin classes that are registered with the Django
Admin site.
"""

from django.contrib import admin

from vast_pipeline.models import *


# set the site title, header
# Text to put at the end of each page's <title>.
admin.site.site_title = 'Vast pipeline site'
# Text to put in each page's <h1> (and above login form).
admin.site.site_header = 'Vast Pipeline Administration'


class RunAdmin(admin.ModelAdmin):
    """
    The RunAdmin class.
    """
    list_display = ('name', 'time', 'status')
    list_filter = ('time', 'status')
    exclude = ('path',)

admin.site.register(Run, RunAdmin)


class ImageAdmin(admin.ModelAdmin):
    """
    The ImageAdmin class.
    """
    list_display = ('name', 'ra', 'dec', 'datetime')
    exclude = ('measurements_path', 'path', 'noise_path', 'background_path')
    search_fields = ('name',)

admin.site.register(Image, ImageAdmin)


admin.site.register(Band)


class SkyRegionAdmin(admin.ModelAdmin):
    """
    The SkyRegionAdmin class.
    """
    list_display = ('__str__', 'centre_ra', 'centre_dec')

admin.site.register(SkyRegion, SkyRegionAdmin)


class SourceAdmin(admin.ModelAdmin):
    """
    The SourceAdmin class.
    """
    list_display = ('name', 'wavg_ra', 'wavg_dec', 'new')
    list_filter = ('new',)
    search_fields = ('name',)

admin.site.register(Source, SourceAdmin)


class MeasurementAdmin(admin.ModelAdmin):
    """
    The MeasurementAdmin class.
    """
    list_display = ('name', 'ra', 'dec', 'forced')
    list_filter = ('forced',)
    search_fields = ('name',)

admin.site.register(Measurement, MeasurementAdmin)


class SourceFavAdmin(admin.ModelAdmin):
    """
    The SourceFavAdmin class.
    """
    list_display = ('user', 'source', 'comment')
    list_filter = ('user',)
    search_fields = ('user','source')

admin.site.register(SourceFav, SourceFavAdmin)
