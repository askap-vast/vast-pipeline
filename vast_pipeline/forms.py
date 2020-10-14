from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from vast_pipeline.models import Comment, Run


class PipelineRunForm(forms.Form):
    run_name = forms.CharField(
        max_length=Run._meta.get_field('name').max_length
    )
    run_description = forms.CharField(widget=forms.Textarea(), required=False)
    monitor = forms.BooleanField(required=False)
    monitor_min_sigma = forms.FloatField()
    monitor_edge_buffer_scale = forms.FloatField()
    monitor_cluster_threshold = forms.FloatField()
    monitor_allow_nan = forms.BooleanField(required=False)
    association_method = forms.CharField()
    association_radius = forms.FloatField()
    association_de_ruiter_radius = forms.FloatField()
    association_parallel = forms.BooleanField(required=False)
    association_epoch_duplicate_radius = forms.FloatField()
    astrometric_uncertainty_ra = forms.FloatField()
    astrometric_uncertainty_dec = forms.FloatField()
    new_source_min_sigma = forms.FloatField()
    default_survey = forms.CharField()
    association_beamwidth_limit = forms.FloatField()
    flux_perc_error = forms.FloatField()
    selavy_local_rms_zero_fill_value = forms.FloatField()
    use_condon_errors = forms.BooleanField(required=False)
    create_measurements_arrow_file = forms.BooleanField(required=False)
    suppress_astropy_warnings = forms.BooleanField(required=False)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("comment", rows=2),
        )
        self.helper.add_input(Submit("submit", "Submit"))
