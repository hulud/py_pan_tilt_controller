import pandas as pd
import plotly.graph_objs as go

# 1) Read the CSV created by your tracking script
df = pd.read_csv("saved/tilt_calibration/tracked/tilt_tracking_results.csv")

# 2) Sort by tilt (optional) if you want a smooth left-to-right line
df = df.sort_values(by="tilt")

# 3) Create a Plotly figure
fig = go.Figure()

# 4) Add traces: one for avg_dx vs tilt, one for avg_dy vs tilt
fig.add_trace(go.Scatter(
    x=df["tilt"],
    y=df["avg_dx"],
    name="Average Δx",
    mode="lines+markers"
))
fig.add_trace(go.Scatter(
    x=df["tilt"],
    y=df["avg_dy"],
    name="Average Δy",
    mode="lines+markers"
))

# 5) Customize layout
fig.update_layout(
    title="Tilt Tracking Results",
    xaxis_title="Tilt (degrees)",
    yaxis_title="Pixel Shift",
    legend=dict(x=0.02, y=0.98)  # place legend in the upper left corner
)

# 6) Show the interactive chart
fig.show()
