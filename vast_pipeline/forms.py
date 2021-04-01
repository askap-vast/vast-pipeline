from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
import tagulous.forms
import tagulous.models
from vast_pipeline.models import Comment, Source, Run


class PipelineRunForm(forms.Form):
    """
    Class for the form used in the creation of a new pipeline run through the
    webserver.
    """
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
    source_aggregate_pair_metrics_min_abs_vs = forms.FloatField()
    use_condon_errors = forms.BooleanField(required=False)
    create_measurements_arrow_files = forms.BooleanField(required=False)
    suppress_astropy_warnings = forms.BooleanField(required=False)


class CommentForm(forms.ModelForm):
    """
    The form used for users to leave comments on objects.
    """
    class Meta:
        model = Comment
        fields = ["comment"]

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialise a CommentForm.

        Returns:
            None.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("comment", rows=2),
        )
        self.helper.add_input(Submit("submit", "Submit"))


class TagWithCommentsForm(forms.Form):
    """
    Class to combined tags with the CommentsForm.
    """
    comment = forms.CharField(required=False, widget=forms.Textarea())
    tags = tagulous.forms.TagField(
        required=False,
        tag_options=tagulous.models.TagOptions(**Source.tags.tag_options.items()),
    )

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialise a TagWithCommentsForm.

        Returns:
            None.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("tags"),
            Field(
                "comment",
                rows=2,
                placeholder=(
                    "Optional. If changing the tags, you should provide justification here."
                ),
            ),
            Submit("submit", "Submit", css_class="btn-block"),
        )
