from django.contrib import admin

from .models import *


# set the site title, header
# Text to put at the end of each page's <title>.
admin.site.site_title = 'Vast pipeline site'
# Text to put in each page's <h1> (and above login form).
admin.site.site_header = 'Vast Pipeline Administration'


class RunAdmin(admin.ModelAdmin):
    list_display = ('name', 'time', 'status')
    list_filter = ('time', 'status')
    exclude = ('path',)

admin.site.register(Run, RunAdmin)


class ImageAdmin(admin.ModelAdmin):
    list_display = ('name', 'ra', 'dec', 'datetime')
    exclude = ('measurements_path', 'path', 'noise_path', 'background_path')
    search_fields = ('name',)

admin.site.register(Image, ImageAdmin)


admin.site.register(Band)


class SkyRegionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'centre_ra', 'centre_dec')

admin.site.register(SkyRegion, SkyRegionAdmin)


class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'wavg_ra', 'wavg_dec', 'new')
    list_filter = ('new',)
    search_fields = ('name',)

admin.site.register(Source, SourceAdmin)


class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('name', 'ra', 'dec', 'forced')
    list_filter = ('forced',)
    search_fields = ('name',)

admin.site.register(Measurement, MeasurementAdmin)
