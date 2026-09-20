"""
Shared chart theming: a validated categorical palette (fixed hue order),
single-hue sequential ramp for magnitude, a blue<->red diverging pair for
sentiment, and reserved status colors for urgency. Values come from the
project's validated default design-system palette so charts stay
colorblind-safe and readable in one system.
"""

import plotly.graph_objects as go
import plotly.io as pio

SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Fixed categorical hue order -- never cycled, never reordered per-chart.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Single-hue sequential ramp (blue), light -> dark, for magnitude encodings.
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

# Diverging pair for sentiment (negative <-> positive), neutral gray midpoint.
DIVERGING_NEG = "#e34948"
DIVERGING_POS = "#2a78d6"
DIVERGING_MID = "#f0efec"

# Reserved status colors -- never reused for a generic series.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

URGENCY_COLOR = {
    "low": STATUS["good"],
    "medium": STATUS["warning"],
    "high": STATUS["serious"],
    "critical": STATUS["critical"],
}
URGENCY_ICON = {"low": "\U0001F7E2", "medium": "\U0001F7E1", "high": "\U0001F7E0", "critical": "\U0001F534"}
URGENCY_ORDER = ["low", "medium", "high", "critical"]

LOB_ORDER = [
    "Retail & Consumer Banking",
    "Credit Cards",
    "Fraud & Disputes",
    "Mortgage & Home Lending",
    "Auto Finance",
    "Small Business Banking",
]
LOB_COLOR = {lob: CATEGORICAL[i % len(CATEGORICAL)] for i, lob in enumerate(LOB_ORDER)}

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def apply_layout(fig: go.Figure, title=None, y_title=None, x_title=None, show_legend=None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY, size=13),
        title=dict(text=title, font=dict(size=15, color=TEXT_PRIMARY)) if title else None,
        margin=dict(l=10, r=10, t=40 if title else 20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=TEXT_SECONDARY)),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT_FAMILY)),
    )
    if show_legend is not None:
        fig.update_layout(showlegend=show_legend)
    fig.update_xaxes(title=x_title, gridcolor=GRIDLINE, linecolor=BASELINE, tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(title=y_title, gridcolor=GRIDLINE, linecolor=BASELINE, tickfont=dict(color=TEXT_MUTED))
    return fig


def register_default_template():
    pio.templates.default = "plotly_white"
