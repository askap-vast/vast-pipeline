"""Contains plotting code used by the web server."""
import colorcet as cc
import holoviews as hv
import networkx as nx
import numpy as np
import pandas as pd

from astropy.stats import sigma_clip, mad_std
from bokeh.models import (
    ColumnDataSource,
    Span,
    BoxAnnotation,
    CustomJS,
    DataRange1d,
    Range1d,
    Whisker,
    LabelSet,
    HoverTool,
    TapTool,
    Slider,
    Button,
    RadioButtonGroup,
    Scatter,
    WheelZoomTool,
    ColorBar
)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.layouts import row, Row, gridplot, Spacer, column
from bokeh.plotting import figure
from bokeh.transform import factor_cmap, linear_cmap
from datetime import timedelta
from django.conf import settings
from django.db.models import F
from holoviews.operation.datashader import datashade, spread
from scipy.stats import norm
from typing import Tuple

from vast_pipeline.models import Measurement, Source


def plot_lightcurve(
    source: Source,
    vs_abs_min: float = 4.3,
    m_abs_min: float = 0.26,
    use_peak_flux: bool = True,
) -> Row:
    """Create the lightcurve and 2-epoch metric graph for a source with Bokeh.

    Args:
        source (Source): Source object.
        vs_abs_min (float, optional): pairs of Measurement objects with an absolute vs metric
            greater than `vs_abs_min` and m metric greater than `m_abs_min` will be connected
            in the metric graph. Defaults to 4.3.
        m_abs_min (float, optional): See `vs_abs_min`. Defaults to 0.26.
        use_peak_flux (bool, optional): If True, use peak fluxes, otherwise use integrated
            fluxes. Defaults to True.

    Returns:
        Row: Bokeh Row layout object containing the lightcurve and graph plots.
    """
    PLOT_WIDTH = 800
    PLOT_HEIGHT = 300
    flux_column = "flux_peak" if use_peak_flux else "flux_int"
    metric_suffix = "peak" if use_peak_flux else "int"
    measurements_qs = (
        Measurement.objects.filter(source__id=source.id)
        .annotate(
            taustart_ts=F("image__datetime"),
            flux=F(flux_column),
            flux_err_lower=F(flux_column) - F(f"{flux_column}_err"),
            flux_err_upper=F(flux_column) + F(f"{flux_column}_err"),
        )
        .values(
            "id",
            "pk",
            "taustart_ts",
            "flux",
            "flux_err_upper",
            "flux_err_lower",
            "forced",
            "name"
        )
        .order_by("taustart_ts")
    )

    # lightcurve required cols: taustart_ts, flux, flux_err_upper, flux_err_lower, forced
    lightcurve = pd.DataFrame(measurements_qs)
    # remap method values to labels to make a better legend
    lightcurve["method"] = lightcurve.forced.map(
        {True: "Forced", False: "Selavy"}
    )
    lightcurve['cutout'] = lightcurve['id'].apply(
        lambda x: f'/cutout/{x}/normal/?img_type=png'
    )
    lc_source = ColumnDataSource(lightcurve)

    method_mapper = factor_cmap(
        "method", palette="Colorblind3", factors=["Selavy", "Forced"]
    )

    min_y = min(0, lightcurve.flux_err_lower.min())
    max_y = lightcurve.flux_err_upper.max()
    y_padding = (max_y - min_y) * 0.1
    fig_lc = figure(
        plot_width=PLOT_WIDTH,
        plot_height=PLOT_HEIGHT,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        x_range=DataRange1d(default_span=timedelta(days=1)),
        y_range=DataRange1d(start=min_y, end=max_y + y_padding),
    )
    # line source must be a COPY of the data for the scatter source for the hover and
    # selection to work properly, using the same ColumnDataSource will break it
    fig_lc.line("taustart_ts", "flux", source=lightcurve)
    lc_scatter = fig_lc.scatter(
        "taustart_ts",
        "flux",
        marker="circle",
        size=6,
        color=method_mapper,
        nonselection_color=method_mapper,
        selection_color="red",
        nonselection_alpha=1.0,
        hover_color="red",
        alpha=1.0,
        source=lc_source,
        legend_group="method",
    )
    fig_lc.add_layout(
        Whisker(
            base="taustart_ts",
            upper="flux_err_upper",
            lower="flux_err_lower",
            source=lc_source,
        )
    )
    fig_lc.xaxis.axis_label = "Datetime"
    fig_lc.xaxis[0].formatter = DatetimeTickFormatter(days="%F", hours='%H:%M')
    fig_lc.yaxis.axis_label = (
        "Peak flux (mJy/beam)" if use_peak_flux else "Integrated flux (mJy)"
    )

    # determine legend location: either bottom_left or top_left
    legend_location = (
        "top_left"
        if lightcurve.sort_values("taustart_ts").iloc[0].flux < (max_y - min_y) / 2
        else "bottom_left"
    )
    fig_lc.legend.location = legend_location

    # TODO add vs and m metrics to graph edges
    # create plot
    fig_graph = figure(
        plot_width=PLOT_HEIGHT,
        plot_height=PLOT_HEIGHT,
        x_range=Range1d(-1.1, 1.1),
        y_range=Range1d(-1.1, 1.1),
        x_axis_type=None,
        y_axis_type=None,
        sizing_mode="fixed",
    )
    hover_tool_lc_callback = None
    measurement_pairs = source.get_measurement_pairs()
    if len(measurement_pairs) > 0:
        candidate_measurement_pairs_df = pd.DataFrame(measurement_pairs).query(
            f"m_{metric_suffix}.abs() >= {m_abs_min} and vs_{metric_suffix}.abs() >= {vs_abs_min}"
        ).reset_index()
        g = nx.Graph()
        for _row in candidate_measurement_pairs_df.itertuples(index=False):
            g.add_edge(_row.measurement_a_id, _row.measurement_b_id)
        node_layout = nx.circular_layout(g, scale=1, center=(0, 0))

        # add node positions to dataframe
        for suffix in ["a", "b"]:
            pos_df = pd.DataFrame(
                candidate_measurement_pairs_df[f"measurement_{suffix}_id"]
                .map(node_layout)
                .to_list(),
                columns=[f"measurement_{suffix}_x", f"measurement_{suffix}_y"],
            )
            candidate_measurement_pairs_df = candidate_measurement_pairs_df.join(pos_df)
        candidate_measurement_pairs_df["measurement_x"] = list(
            zip(
                candidate_measurement_pairs_df.measurement_a_x.values,
                candidate_measurement_pairs_df.measurement_b_x.values,
            )
        )
        candidate_measurement_pairs_df["measurement_y"] = list(
            zip(
                candidate_measurement_pairs_df.measurement_a_y.values,
                candidate_measurement_pairs_df.measurement_b_y.values,
            )
        )
        node_positions_df = pd.DataFrame.from_dict(
            node_layout, orient="index", columns=["x", "y"]
        )
        node_positions_df["lc_index"] = node_positions_df.index.map(
            {v: k for k, v in lightcurve.id.to_dict().items()}
        ).values.astype(str)
        node_source = ColumnDataSource(node_positions_df)
        edge_source = ColumnDataSource(candidate_measurement_pairs_df)

        # add edges to plot
        edge_renderer = fig_graph.multi_line(
            "measurement_x",
            "measurement_y",
            line_width=5,
            hover_color="red",
            source=edge_source,
            name="edges",
        )
        # add nodes to plot
        node_renderer = fig_graph.circle(
            "x",
            "y",
            size=20,
            hover_color="red",
            selection_color="red",
            nonselection_alpha=1.0,
            source=node_source,
            name="nodes",
        )

        # create hover tool for node edges
        edge_callback_code = """
            // get edge index
            let indices_a = cb_data.index.indices.map(i => edge_data.data.measurement_a_id[i]);
            let indices_b = cb_data.index.indices.map(i => edge_data.data.measurement_b_id[i]);
            let indices = indices_a.concat(indices_b);
            let lightcurve_indices = indices.map(i => lightcurve_data.data.id.indexOf(i));
            lightcurve_data.selected.indices = lightcurve_indices;
        """
        hover_tool_edges = HoverTool(
            tooltips=[
                (f"Vs {metric_suffix}", f"@vs_{metric_suffix}"),
                (f"m {metric_suffix}", f"@m_{metric_suffix}"),
            ],
            renderers=[edge_renderer],
            callback=CustomJS(
                args={
                    "lightcurve_data": lc_scatter.data_source,
                    "edge_data": edge_renderer.data_source,
                },
                code=edge_callback_code,
            ),
        )
        fig_graph.add_tools(hover_tool_edges)
        # create labels for nodes
        graph_source = ColumnDataSource(node_positions_df)
        labels = LabelSet(
            x="x",
            y="y",
            text="lc_index",
            source=graph_source,
            text_align="center",
            text_baseline="middle",
            text_font_size="1em",
            text_color="white",
        )
        fig_graph.renderers.append(labels)

        # prepare a JS callback for the lightcurve hover tool to mark the associated nodes
        hover_tool_lc_callback = CustomJS(
            args={
                "node_data": node_renderer.data_source,
                "lightcurve_data": lc_scatter.data_source,
            },
            code="""
                let ids = cb_data.index.indices.map(i => lightcurve_data.data.id[i]);
                let node_indices = ids.map(i => node_data.data.index.indexOf(i));
                node_data.selected.indices = node_indices;
            """,
        )

    # create hover tool for lightcurve
    hover_tool_lc = HoverTool(
        # tooltips=[
        #     ("Index", "@index"),
        #     ("Date", "@taustart_ts{%F}"),
        #     (f"Flux {metric_suffix}", "@flux mJy"),
        #     ('Cutout', "@cutout")
        # ],
        tooltips="""
        <div style="width:200;">
            <div>
                <img
                    src=@cutout height="100" alt=@cutout width="100"
                    style="float: left; margin: 0px 15px 15px 0px;"
                    border="2"
                ></img>
            </div>
            <div>
                <div style="font-size: 12px; font-weight: bold;">Date: </div>
                <div style="font-size: 12px; color: #966;">@taustart_ts{%F}</div>
            </div>
            <div>
                <div style="font-size: 12px; font-weight: bold;">Flux:</div>
                <div style="font-size: 12px; color: #966;">@flux mJy</div>
            </div>
            <div>
                <div style="font-size: 12px; font-weight: bold;">Index:</div>
                <div style="font-size: 12px; color: #966;">@index</div>
            </div>
        </div>
        """,
        formatters={"@taustart_ts": "datetime", },
        mode="mouse",
        callback=hover_tool_lc_callback,
    )
    fig_lc.add_tools(hover_tool_lc)

    plot_row = row(fig_lc, fig_graph, sizing_mode="stretch_width")
    plot_row.css_classes.append("mx-auto")
    return plot_row


def fit_eta_v(
    df: pd.DataFrame, use_peak_flux: bool = False
) -> Tuple[float, float, float, float]:
    """
    Fits the eta and v distributions with Gaussians. Used from
    within the 'run_eta_v_analysis' method.

    Args:
        df: DataFrame containing the sources from the pipeline run. A
            `pandas.core.frame.DataFrame` instance.
        use_peak_flux: Use peak fluxes for the analysis instead of
            integrated fluxes, defaults to 'False'.

    Returns:
        The mean of the eta fit.
        The sigma of the eta fit.
        The mean of the v fit.
        The sigma of the v fit.
    """

    if use_peak_flux:
        eta_label = 'eta_peak'
        v_label = 'v_peak'
    else:
        eta_label = 'eta_int'
        v_label = 'v_int'

    eta_log = np.log10(df[eta_label])
    v_log = np.log10(df[v_label])

    eta_log_clipped = sigma_clip(
        eta_log, masked=False, stdfunc=mad_std, sigma=3
    )
    v_log_clipped = sigma_clip(
        v_log, masked=False, stdfunc=mad_std, sigma=3
    )

    eta_fit_mean, eta_fit_sigma = norm.fit(eta_log_clipped)
    v_fit_mean, v_fit_sigma = norm.fit(v_log_clipped)

    return (eta_fit_mean, eta_fit_sigma, v_fit_mean, v_fit_sigma)


def plot_eta_v_bokeh(
    source: Source,
    eta_sigma: float,
    v_sigma: float,
    use_peak_flux: bool = True
) -> gridplot:
    """
    Adapted from code written by Andrew O'Brien.
    Produces the eta, V candidates plot
    (see Rowlinson et al., 2018,
    https://ui.adsabs.harvard.edu/abs/2019A%26C....27..111R/abstract).
    Returns a bokeh version.

    Args:
        source: The source model object containing the result of the query.
        eta_sigma: The log10 eta_cutoff from the analysis.
        v_sigma: The log10 v_cutoff from the analysis.
        use_peak_flux: Use peak fluxes for the analysis instead of
            integrated fluxes, defaults to 'True'.

    Returns:
        Bokeh grid object containing figure.
    """

    df = pd.DataFrame(source.values(
        "id", "name", "eta_peak", "eta_int", "v_peak", "v_int", "n_meas_sel"
    ))

    (
        eta_fit_mean, eta_fit_sigma,
        v_fit_mean, v_fit_sigma
    ) = fit_eta_v(df, use_peak_flux=use_peak_flux)

    eta_cutoff_log10 = eta_fit_mean + eta_sigma * eta_fit_sigma
    v_cutoff_log10 = v_fit_mean + v_sigma * v_fit_sigma

    eta_cutoff = 10 ** eta_cutoff_log10
    v_cutoff = 10 ** v_cutoff_log10

    # generate fitted curve data for plotting
    eta_x = np.linspace(
        norm.ppf(0.001, loc=eta_fit_mean, scale=eta_fit_sigma),
        norm.ppf(0.999, loc=eta_fit_mean, scale=eta_fit_sigma),
    )
    eta_y = norm.pdf(eta_x, loc=eta_fit_mean, scale=eta_fit_sigma)

    v_x = np.linspace(
        norm.ppf(0.001, loc=v_fit_mean, scale=v_fit_sigma),
        norm.ppf(0.999, loc=v_fit_mean, scale=v_fit_sigma),
    )
    v_y = norm.pdf(v_x, loc=v_fit_mean, scale=v_fit_sigma)

    if use_peak_flux:
        x_label = 'eta_peak'
        y_label = 'v_peak'
        title = 'Peak Flux'
    else:
        x_label = 'eta_int'
        y_label = 'v_int'
        title = "Int. Flux"

    # PLOTTING NOTE!
    # Datashader does not play nice with setting the axis to log-log, in fact
    # it just doesn't work as of writing.
    # See https://github.com/holoviz/holoviews/issues/2195.
    # So this is why the actual log10 values are plotted instead on a linear
    # axis. This could be revisited if the probelm with datashader and
    # holoviews is resolved.
    for i in [x_label, y_label]:
        df[f"{i}_log10"] = np.log10(df[i])

    PLOT_WIDTH = 700
    PLOT_HEIGHT = PLOT_WIDTH

    x_axis_label = "log \u03B7"
    y_axis_label = "log V"

    cmap = linear_cmap(
        "n_meas_sel",
        cc.kb,
        df["n_meas_sel"].min(),
        df["n_meas_sel"].max(),
    )

    cb_title = "Number of Selavy Measurements"

    if df.shape[0] > settings.ETA_V_DATASHADER_THRESHOLD:

        hv.extension('bokeh')

        # create dfs for bokeh and datashader
        mask = ((df[x_label] >= eta_cutoff) & (df[y_label] >= v_cutoff))

        bokeh_df = df.loc[mask]
        ds_df = df.loc[~mask]

        # create datashader version first
        points = spread(
            datashade(
                hv.Points(ds_df[[f"{x_label}_log10", f"{y_label}_log10"]]),
                cmap="Blues"
            ),
            px=1,
            shape='square'
        ).opts(height=PLOT_HEIGHT, width=PLOT_WIDTH)

        fig = hv.render(points)

        fig.xaxis.axis_label = x_axis_label
        fig.yaxis.axis_label = y_axis_label
        fig.aspect_scale = 1
        fig.sizing_mode = 'stretch_width'
        fig.output_backend = "webgl"
        # update the y axis default range
        if bokeh_df.shape[0] > 0:
            fig.y_range.end = bokeh_df[f'{y_label}_log10'].max() + 0.2

        cb_title += " (interactive points only)"
    else:
        bokeh_df = df

        fig = figure(
            output_backend="webgl",
            plot_width=PLOT_WIDTH,
            plot_height=PLOT_HEIGHT,
            aspect_scale=1,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            sizing_mode="stretch_width",
        )

    # activate scroll wheel zoom by default
    fig.toolbar.active_scroll = fig.select_one(WheelZoomTool)

    source = ColumnDataSource(data=bokeh_df)

    bokeh_points = Scatter(
        x=f"{x_label}_log10",
        y=f"{y_label}_log10",
        fill_color=cmap,
        line_color=cmap,
        marker="circle",
        size=5
    )

    bokeh_g1 = fig.add_glyph(source_or_glyph=source, glyph=bokeh_points)

    hover = HoverTool(
        renderers=[bokeh_g1],
        tooltips=[
            ("source", "@name"),
            ("\u03B7", f"@{x_label}"),
            ("V", f"@{y_label}"),
            ("id", "@id")
        ],
        mode='mouse'
    )

    fig.add_tools(hover)

    color_bar = ColorBar(
        color_mapper=cmap['transform'],
        title=cb_title
    )

    fig.add_layout(color_bar, 'below')

    # axis histograms
    # filter out any forced-phot points for these
    x_hist = figure(
        plot_width=PLOT_WIDTH,
        plot_height=100,
        x_range=fig.x_range,
        y_axis_type=None,
        x_axis_type="linear",
        x_axis_location="above",
        sizing_mode="stretch_width",
        title="VAST eta-V {}".format(title),
        tools="",
        output_backend="webgl",
    )
    x_hist_data, x_hist_edges = np.histogram(
        df[f"{x_label}_log10"], density=True, bins=50,
    )
    x_hist.quad(
        top=x_hist_data,
        bottom=0,
        left=x_hist_edges[:-1],
        right=x_hist_edges[1:],
    )
    x_hist.line(eta_x, eta_y, color="black")
    x_hist_sigma_span = Span(
        location=eta_cutoff_log10,
        dimension="height",
        line_color="black",
        line_dash="dashed",
    )
    x_hist.add_layout(x_hist_sigma_span)
    fig.add_layout(x_hist_sigma_span)

    y_hist = figure(
        plot_height=PLOT_HEIGHT,
        plot_width=100,
        y_range=fig.y_range,
        x_axis_type=None,
        y_axis_type="linear",
        y_axis_location="right",
        sizing_mode="stretch_height",
        tools="",
        output_backend="webgl",
    )
    y_hist_data, y_hist_edges = np.histogram(
        (df[f"{y_label}_log10"]), density=True, bins=50,
    )
    y_hist.quad(
        right=y_hist_data,
        left=0,
        top=y_hist_edges[:-1],
        bottom=y_hist_edges[1:],
    )
    y_hist.line(v_y, v_x, color="black")
    y_hist_sigma_span = Span(
        location=v_cutoff_log10,
        dimension="width",
        line_color="black",
        line_dash="dashed",
    )
    y_hist.add_layout(y_hist_sigma_span)
    fig.add_layout(y_hist_sigma_span)

    variable_region = BoxAnnotation(
        left=eta_cutoff_log10,
        bottom=v_cutoff_log10,
        fill_color="orange",
        fill_alpha=0.3,
        level="underlay",
    )
    fig.add_layout(variable_region)

    eta_slider = Slider(
        start=0,
        end=10,
        step=0.1,
        value=eta_sigma,
        title="\u03B7 sigma value",
        sizing_mode='stretch_width'
    )
    v_slider = Slider(
        start=0,
        end=10,
        step=0.1,
        value=v_sigma,
        title="V sigma value",
        sizing_mode='stretch_width'
    )

    labels = ['Peak', 'Integrated']
    active = 0 if use_peak_flux else 1
    flux_choice_radio = RadioButtonGroup(
        labels=labels,
        active=active,
        sizing_mode='stretch_width'
    )

    button = Button(
        label="Apply",
        button_type="primary",
        sizing_mode='stretch_width'
    )
    button.js_on_click(
        CustomJS(
            args=dict(
                eta_slider=eta_slider,
                v_slider=v_slider,
                button=button,
                flux_choice_radio=flux_choice_radio
            ),
            code="""
            button.label = "Loading..."
            var e = eta_slider.value;
            var v = v_slider.value;
            const peak = ["peak", "int"];
            var fluxType = peak[flux_choice_radio.active];
            getEtaVPlot(e, v, fluxType);
            """
        )
    )

    grid = gridplot(
        [
            [x_hist, Spacer(width=100, height=100)],
            [fig, y_hist],
        ]
    )

    plot_column = column(
        grid,
        flux_choice_radio,
        eta_slider,
        v_slider,
        button,
        sizing_mode='stretch_width'
    )

    plot_column.css_classes.append("mx-auto")

    source = ColumnDataSource(data=bokeh_df)
    callback = CustomJS(
        args=dict(source=source, flux_choice_radio=flux_choice_radio),
        code="""
        const d1 = source.data;
        const i = cb_data.source.selected.indices[0];
        const id = d1['id'][i];
        const peak = ["peak", "int"];
        var fluxType = peak[flux_choice_radio.active];

        $(document).ready(function () {
          update_card(id);
          getLightcurvePlot(id, fluxType);
        });
        """
    )

    tap = TapTool(callback=callback, renderers=[bokeh_g1])
    fig.tools.append(tap)

    plot_row = row(plot_column, sizing_mode="stretch_width")
    plot_row.css_classes.append("mx-auto")

    return plot_row
