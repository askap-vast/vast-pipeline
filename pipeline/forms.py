from django import forms
from .models import Run


class PipelineRunForm(forms.Form):
    run_name = forms.CharField(
        max_length=Run._meta.get_field('name').max_length
    )
    run_comment = forms.CharField(widget=forms.Textarea(), required=False)
    monitor = forms.BooleanField(required=False)
    monitor_min_sigma = forms.FloatField()
    monitor_edge_buffer_scale = forms.FloatField()
    monitor_cluster_threshold = forms.FloatField()
    monitor_allow_nan = forms.BooleanField(required=False)
    association_method = forms.CharField()
    astrometric_uncertainty_ra = forms.FloatField()
    association_radius = forms.FloatField()
    astrometric_uncertainty_dec = forms.FloatField()
    association_de_ruiter_radius = forms.FloatField()
    new_source_min_sigma = forms.FloatField()
    default_survey = forms.CharField()
    association_beamwidth_limit = forms.FloatField()
    flux_perc_error = forms.FloatField()
    selavy_local_rms_zero_fill_value = forms.FloatField()
    use_condon_errors = forms.BooleanField(required=False)
    suppress_astropy_warnings = forms.BooleanField(required=False)
