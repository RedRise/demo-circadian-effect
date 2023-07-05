import os
import numpy as np
import pandas as pd
from plotly import subplots
import plotly.express as px
import plotly.graph_objects as go
import pytz

# load data
filepath = os.path.join("data", "Binance_ETHUSDC_1h.csv")
PAIR = "ETH/USDC"

hdf = pd.read_csv(filepath, skiprows=1)
hdf["DateTime"] = pd.to_datetime(hdf["Date"], utc=True).dt.tz_convert(pytz.timezone('EST'))
hdf["Date"] = hdf["DateTime"].dt.date
hdf["Hour"] = hdf["DateTime"].dt.hour
hdf.head()

# plot ETH volume by hour
hmean = (
    hdf.groupby("Hour")
    .apply(lambda x: x["Volume ETH"].mean())
    .reset_index(name="Mean Volume")
)
px.bar(hmean, x="Hour", y="Mean Volume", title=PAIR + " Mean Volume by Hour (EST)").show()


# utility fonction to compute stats on returns
def stats(s):
    c = s["Return"]
    return pd.Series({"Mean": c.mean() * 365, "Std": c.std() * np.sqrt(365)})

def compute_class(hdf, closing_hour, day_length, should_sort=True):
    hour_start = (closing_hour - day_length) % 24

    if should_sort:
        hdf = hdf.set_index("Unix").sort_index()

    pdf = hdf.copy()
    pdf = pdf.loc[pdf["Hour"].isin([hour_start, closing_hour])]

    pdf["LogPrice"] = np.log(pdf["Close"])
    pdf["Return"] = pdf["LogPrice"].diff()

    pdf["Class"] = pdf.apply(
        lambda x: "day" if x["Hour"] == closing_hour else "night", axis=1
    )

    return pdf


def stats_by_class(hdf, closing_hour, day_length, should_sort=True):
    pdf = compute_class(hdf, closing_hour, day_length, should_sort)

    rdf = pdf.groupby("Class").apply(stats)
    rdf["Close"] = closing_hour
    rdf["DayLength"] = day_length

    return rdf.reset_index()


def all_stats(hdf, closing_hours, day_lengths):
    hdf = hdf.set_index("Unix").sort_index()
    res = []

    for ch in closing_hours:
        for dl in day_lengths:
            res.append(stats_by_class(hdf, ch, dl, should_sort=False))

    res = pd.concat(res, axis=0).reset_index(drop=True)
    res["Sharpe"] = res["Mean"] / res["Std"]
    return res


# produce stats for a large combination of closing hours and day lengths
rdf = all_stats(hdf, range(0, 24), range(6, 12))

# plotting heatmaps
varName = "Sharpe"

fig = subplots.make_subplots(
    rows=1, cols=2, print_grid=False, shared_yaxes=True, subplot_titles=("Day", "Night")
)

ldf = rdf.loc[rdf["Class"] == "day"]
fig.append_trace(
    go.Heatmap(
        x=ldf["DayLength"], y=ldf["Close"], z=ldf[varName], coloraxis="coloraxis"
    ),
    1,
    1,
)

ldf = rdf.loc[rdf["Class"] == "night"]
fig.append_trace(
    go.Heatmap(
        x=ldf["DayLength"], y=ldf["Close"], z=ldf[varName], coloraxis="coloraxis"
    ),
    1,
    2,
)

fig = fig.update_layout(
    title_text=PAIR + " " + varName + " during Day and Night",
    coloraxis={"colorscale": "thermal"},
    yaxis={"title": "Closing Hour (EST)"},
    xaxis={"title": "Day Length (h)"}
)
fig.show()


# plotting time series
ch = 14 # closing hour
dl = 6  # day length
pdf = compute_class(hdf, ch, dl)

tdf = (
    pdf.reset_index()[["Date", "Class", "Return"]]
    .set_index("Date")
    .fillna(0)
    .groupby("Class")
    .apply(lambda x: x["Return"].cumsum())
    .reset_index(name="Return")
)
px.line(
    tdf,
    x="Date",
    y="Return",
    color="Class",
    title="{0} cumulated returns Day vs. Night. Close: {1}h, Day Length: {2}h (EST)".format(
        PAIR, ch, dl
    ),
).show()
