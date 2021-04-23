"""Contains plotting code used by the web server."""

from datetime import timedelta
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    DataRange1d,
    Range1d,
    Whisker,
    LabelSet,
    HoverTool,
)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.layouts import row, Row
from bokeh.plotting import figure
from bokeh.transform import factor_cmap
from django.db.models import F
from django.db.models.functions import Abs
import pandas as pd
import networkx as nx

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
        vs_abs_min (float, optional): MeasurementPair objects with an absolute vs metric
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
        )
        .order_by("taustart_ts")
    )
    candidate_measurement_pairs_qs = (
        source.measurementpair_set.annotate(
            m_abs=Abs(f"m_{metric_suffix}"), vs_abs=Abs(f"vs_{metric_suffix}")
        )
        .filter(vs_abs__gte=vs_abs_min, m_abs__gte=m_abs_min)
        .values("measurement_a_id", "measurement_b_id", "vs_abs", "m_abs")
    )
    candidate_measurement_pairs_df = pd.DataFrame(candidate_measurement_pairs_qs)

    # lightcurve required cols: taustart_ts, flux, flux_err_upper, flux_err_lower, forced
    lightcurve = pd.DataFrame(measurements_qs)
    # remap method values to labels to make a better legend
    lightcurve["method"] = lightcurve.forced.map({True: "Forced", False: "Selavy"})
    source = ColumnDataSource(lightcurve)
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
        source=source,
        legend_group="method",
    )
    fig_lc.add_layout(
        Whisker(
            base="taustart_ts",
            upper="flux_err_upper",
            lower="flux_err_lower",
            source=source,
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
    if len(candidate_measurement_pairs_df) > 0:
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
        ).values
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
            tooltips=None,
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
        tooltips=[
            ("Index", "@index"),
            ("Date", "@taustart_ts{%F}"),
            (f"Flux {metric_suffix}", "@flux mJy"),
        ],
        formatters={"@taustart_ts": "datetime", },
        mode="vline",
        callback=hover_tool_lc_callback,
    )
    fig_lc.add_tools(hover_tool_lc)

    plot_row = row(fig_lc, fig_graph, sizing_mode="stretch_width")
    plot_row.css_classes.append("mx-auto")
    return plot_row
