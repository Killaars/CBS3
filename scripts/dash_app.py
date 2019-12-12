# %%
'''
TODO
- Realtime naar 15 minuten vanaf nu

DONE
- Zelfde vrachtwagen minder vaak meetellen --> gemiddelde per punt
- verschillende zooms --> van segment naar wegniveau en linkerbaan/rechterbaan
- Resetten of niet na actie
- Alleen data in graph bekijken. Hoge zoom niveaus dus alleen lokale data
- Naar CSS kijken
- Daily or hourly mode
- Buttons etc op de goede plek
- Bootstrap components
- Nederlands of engels? --> Nederlands
- Stresstest --> bij 250.000 records werkt het nog steeds best prima
- Monitoring mode with https://dash.plot.ly/live-updates
- denken over einddatum
- dynamic layout

'''
# %%
from pathlib import Path
import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np

from variables import token
from project_functions import P3 as zoom_curve
from project_functions import get_color, get_linewidth, determine_bbox, read_input_csv

# Set paths/filenames etc
path = Path('/home/killaarsl/Documents/CBS3_visualization/')  # Main directory
filename = 'data/output/proxy_data_withdec.csv'

# Read csv file
# First read is done here, some variables are extracted from this
# Afterwards, updated every minute in def update_data
df = read_input_csv(path, filename)

# converting to json format
df_json = df.to_json(date_format='iso', orient='split')

road_lats = [df[df['road'] == x][['Camera_id', 'lat']].sort_values(
    by='Camera_id').drop_duplicates(subset='Camera_id')['lat'].values for x in df['road'].unique()]
road_lons = [df[df['road'] == x][['Camera_id', 'lon']].sort_values(
    by='Camera_id').drop_duplicates(subset='Camera_id')['lon'].values for x in df['road'].unique()]
road_points = pd.DataFrame({'lats': road_lats,
                            'lons': road_lons}, index=df['road'].unique())

# Create df with number of cameras for the entire road
nr_cameras = pd.DataFrame({'nr_cameras': [len(df[df['road'] == x]['Camera_id'].unique()) for x in df['road'].unique()]},
                          index=df['road'].unique())

# Get first and last timestamp, in order to get first and last dates and times
# First from the data and last is current time
mn = min(df['timestamp'])
mx = pd.to_datetime(datetime.datetime.now())

# %%
# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport",
         "content": "width=device-width, initial-scale=1.0"}
    ],
)

app.layout = html.Div(
    children=[
        html.Div(
            id="body",
            # className="container scalable",
            children=[
                html.Div(
                    className="two columns",
                    id="left-column",
                    children=[
                        # Two breaks to get it on the save level
                        # as the graph block
                        html.Br(),
                        html.Br(),
                        # Group to select the mode of the graph
                        dbc.FormGroup([
                            dbc.Label('Kies een mode: '),
                            dbc.RadioItems(
                                id='mode',
                                options=[{'label': i, 'value': i} for i in ['Realtime', 'Alles']],
                                value='Alles',
                                labelStyle={'display': 'inline-block'},
                                )
                            ]),
                        html.Br(),
                        # Group to select the GEVI codes
                        dbc.FormGroup([
                            dbc.Label('Kies GEVI codes: '),
                            dcc.Dropdown(
                                id='gevi_selector',
                                options=[{'label': i, 'value': i} for i in np.sort(df['gevi'].unique())],
                                multi=True,
                                value=[]),
                            ]),
                        html.Br(),
                        dbc.FormGroup(
                            id='date_formgroup',
                            children=[
                                dbc.Label('Kies start en eind datum:'),
                                dcc.DatePickerSingle(
                                    id="start_date",
                                    min_date_allowed=datetime.datetime(
                                        mn.year, mn.month, mn.day),
                                    max_date_allowed=datetime.datetime(
                                        mx.year, mx.month, mx.day),
                                    initial_visible_month=datetime.datetime(
                                        mn.year, mn.month, mn.day),
                                    date=datetime.datetime(
                                        mn.year, mn.month, mn.day),
                                    display_format="MMMM D, YYYY",
                                    style={"border": "0px solid black"},
                                ),
                                dcc.DatePickerSingle(
                                    id="end_date",
                                    min_date_allowed=datetime.datetime(
                                        mn.year, mn.month, mn.day),
                                    max_date_allowed=datetime.datetime(
                                        mx.year, mx.month, mx.day),
                                    initial_visible_month=datetime.datetime(
                                        mx.year, mx.month, mx.day),
                                    date=datetime.datetime(
                                        mx.year, mx.month, mx.day),
                                    display_format="MMMM D, YYYY",
                                    style={"border": "0px solid black"},
                                    ),
                                ],
                            ),
                        html.Br(),
                        # Checkboxes to determine the filtering
                        dbc.FormGroup([
                            dbc.Label('Kies filter detail:'),
                            dbc.Checklist(
                                id='filteroptions',
                                options=[
                                    {"label": "Gemiddeld dagelijks patroon", "value": 'daily'},
                                    {"label": "Alleen specifieke uren", "value": 'hourly'},
                                    ],
                                labelStyle={'display': 'inline-block'},
                                value=[]
                                )
                            ]),
                        html.Br(),
                        dbc.FormGroup(
                            id='hour_formgroup',
                            children=[
                                dbc.Label('Uren tussen:'),
                                dcc.RangeSlider(
                                    id='hour-slider',
                                    count=1,
                                    min=0,
                                    max=24,
                                    step=1,
                                    marks={i: '{}:00'.format(i) for i in range(0, 28, 4)},
                                    value=[0, 24]
                                    ),
                                html.Br(),
                                ], style={"display": "none"}
                            ),
                        dbc.FormGroup([
                            dcc.Interval(
                                id='interval-component',
                                interval=60*1000, # in milliseconds, every minute
                                n_intervals=0
                                )
                            ]),
                        ],
                    style={'marginLeft': '1em'}
                    ),
                html.Div(
                    className="nine columns",
                    children=[
                        html.H2(
                            id="banner-title",
                            children=[
                                html.A(
                                    "Intensiteit van vrachtwagens met gevaarlijke stoffen over de Nederlandse snelwegen",
                                    href="https://github.com/Killaars/CBS3",
                                    style={
                                        "text-decoration": "none",
                                        "color": "inherit",
                                    },
                                )
                            ],
                        ),
                        html.Div(children=[
                            dcc.Graph(id='mapbox_graph',
                                      hoverData={'points': [{'lat': 52.3128, 'lon': 7.0391}]},
                                      relayoutData={'mapbox.zoom': 6.5},
                                      )
                            ],
                            style={'width': '69%', 'display': 'inline-block', 'padding': '0 20'}
                            ),
                        html.Div(children=[
                            dcc.Graph(id='timeseries')],
                            style={'display': 'inline-block', 'width': '29%', 'vertical-align': 'top'}
                            ),
                        ]
                    ),
                ]
            ),
        # Hidden div inside the app that stores the refreshed data
        # Updated every minute
        html.Div(id='refreshed_data', style={'display': 'none'}),
        # Hidden div inside the app that stores the filtered data
        html.Div(id='filtered_data',
                 style={'display': 'none'}),
        ]
    )


@app.callback(Output('refreshed_data', 'children'),
              [Input('interval-component', 'n_intervals')])
def update_data(n_intervals):
    '''
    Check the file for new data every minute
    '''
    new_df = read_input_csv(path, filename)
    return new_df.to_json(date_format='iso', orient='split')


@app.callback(Output('hour_formgroup', 'style'),
              [Input('filteroptions', 'value')])
def show_hours(filteroptions):
    '''
    Only show hourly if it makes sense
    '''
    if 'hourly' in filteroptions:
        to_return = {}
    else:
        to_return = {'display': 'none'}
    return to_return


@app.callback(
    Output('filtered_data', 'children'),
    [Input('mode', 'value'),
     Input('gevi_selector', 'value'),
     Input('start_date', 'date'),
     Input('end_date', 'date'),
     Input('mapbox_graph', 'relayoutData'),
     Input('filteroptions', 'value'),
     Input('hour-slider', 'value'),
     Input('refreshed_data', 'children'),
     ])
def filter_data(selected_mode,
                selected_gevi,
                start_date,
                end_date,
                relayoutdata,
                filteroptions,
                hourslider,
                jsonified_refreshed_data):
    '''
    Filter data callback
    Reads refreshed data given by update_data
    Filters and stores the df as json, other graphs can use it as input
    '''
    # Load data from hidden div, if possible
    try:
        dff = pd.read_json(jsonified_refreshed_data, orient='split')
    except:
        dff = pd.read_json(df_json, orient='split')

    # Realtime
    if selected_mode == 'Realtime':
        timecutoff = max(dff['timestamp']) - datetime.timedelta(minutes=15)
        filtered_df = dff[dff['timestamp'] >= timecutoff]

    # Aggregated
    if selected_mode == 'Alles':
        filtered_df = dff.copy()

        # Daily filtering --> between or equal to start/end date
        filtered_df = filtered_df[(filtered_df['timestamp'] >= start_date) &
                                  (filtered_df['timestamp'] <= end_date)]

        # Hourly filtering --> Between certain hours, irrespective of date
        if 'hourly' in filteroptions:
            index = pd.DatetimeIndex(filtered_df['timestamp'])
            begin_time = '%s:00' % (hourslider[0])
            end_time = '%s:00' % (hourslider[1])
            if hourslider[1] == 24:
                end_time = '23:59'
            filtered_df = filtered_df.iloc[index.indexer_between_time(begin_time, end_time)]

    # Filter gevi codes based on selection
    if len(selected_gevi) > 0:
        filtered_df = filtered_df[filtered_df['gevi'].isin(selected_gevi)]

    # Filter based on zoom window
    if 'mapbox.zoom' in relayoutdata:
        if relayoutdata['mapbox.zoom'] > 8.5:
            maxlat, maxlon, minlat, minlon = determine_bbox(
                relayoutdata['mapbox.zoom'],
                relayoutdata['mapbox.center']['lat'],
                relayoutdata['mapbox.center']['lon'],
                zoom_curve)

            filtered_df = filtered_df[(filtered_df['lat'] >= minlat) &
                                      (filtered_df['lat'] <= maxlat) &
                                      (filtered_df['lon'] >= minlon) &
                                      (filtered_df['lon'] <= maxlon)]
    return filtered_df.to_json(date_format='iso', orient='split')


# Update main figure callback
@app.callback(
    Output('mapbox_graph', 'figure'),
    [Input('filtered_data', 'children'),
     Input('mapbox_graph', 'relayoutData'),
     ])
def update_figure(jsonified_filtered_data, relayoutdata):
    '''
    Builds mapbox graph graph. Uses filtered data from filter_data.
    Calculates intensity for the road pieces and determines color and
    linewidth based on this
    '''

    # Add default zoom if not present in relayoutData
    if 'mapbox.zoom' not in relayoutdata:
        relayoutdata['mapbox.zoom'] = 6.5
    print(relayoutdata)
    # Load data from hidden div
    dff = pd.read_json(jsonified_filtered_data, orient='split')

    # Zoom smaller than XXXX --> aggregates per road.
    # Segment and travel direction in hoverinfo
    if relayoutdata['mapbox.zoom'] < 9.5:
        # If one or more entries, fill plot_data graph,
        # else, return empty trace
        if len(dff) > 0:
            # Bepalen max_intensity of all roads
            max_intensity = max(dff['road'].value_counts()/nr_cameras['nr_cameras'])

            # Bepalen intensiteit per road
            plot_data = []
            for road in dff['road'].unique():
                intensity = len(dff[dff['road'] == road])/nr_cameras.loc[road, 'nr_cameras']
                plot_data.append(dict(type='scattermapbox',
                                      lat=road_points.loc[road, 'lats'],
                                      lon=road_points.loc[road, 'lons'],
                                      mode='lines',
                                      text=str(intensity),
                                      line=dict(width=get_linewidth(intensity, max_intensity),
                                                color=get_color(intensity, max_intensity)),
                                      showlegend=True,
                                      name=road,
                                      hoverinfo='text'
                                      ))
        else:
            plot_data = []

    # Zoom smaller than XXXX --> aggregates per segment. Travel direction in hoverinfo
    if relayoutdata['mapbox.zoom'] >= 9.5:
        if len(dff) > 0:
            # Determine maximum intensity for each segment
            # first for each travel direction
            max_intensity = []
            for direction in dff['direction'].unique():
                temp_df = dff[dff['direction'] == direction]
                max_intensity.append(max([max(temp_df[temp_df['road'] == x]['Camera_id'].value_counts()) for x in temp_df['road'].unique()]))
            max_intensity = max(max_intensity)

            # Empty plot data
            plot_data = []

            for direction in dff['direction'].unique():
                temp_df = dff[dff['direction'] == direction]
                for road in temp_df['road'].unique():
                    for segment in temp_df[temp_df['road'] == road]['Camera_id'].unique():
                        intensity = len(temp_df[(temp_df['road'] == road) & (temp_df['Camera_id'] == segment)])

                        # Select coords of this point and the next, if not possible, only this point
                        # The mean of all lat/lon for this segment for this road. Are multiple similar,
                        # mean gives one of those.
                        try:
                            lats = [temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment)]['lat'].mean(),
                                    temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment+1)]['lat'].mean()]
                            lons = [temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment)]['lon'].mean(),
                                    temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment+1)]['lon'].mean()]
                        except:
                            lats = [temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment)]['lat'].mean()]
                            lons = [temp_df[(temp_df['road'] == road) &
                                            (temp_df['Camera_id'] == segment)]['lon'].mean()]

                        plot_data.append(dict(type='scattermapbox',
                                              lat=lats,
                                              lon=lons,
                                              mode='lines',
                                              text='%s - %s - %s' % (intensity, road, direction),
                                              line=dict(width=get_linewidth(intensity, max_intensity),
                                                        color=get_color(intensity, max_intensity)),
                                              showlegend=False,
                                              name=road,
                                              hoverinfo='text'
                                              ))
        else:
            plot_data = []
    # Returns plot_data as data part of plotly graph and filled layout
    return {
        "data": plot_data,
        "layout": dict(
            # autosize = True,
            height=800,
            legend=dict(orientation="h"),
            plot_bgcolor="#1E1E1E", paper_bgcolor="#1E1E1E",
            font=dict(color="#d8d8d8"),
            hovermode="closest",
            margin=dict(l=0, r=0, t=0, b=0),
            # margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
            mapbox=dict(
                uirevision='no reset of zoom',
                accesstoken=token,
                # bearing = 0,
                center=dict(
                    lon=5.104480,
                    lat=52.092876),
                style="light",
                # pitch = 0,
                zoom=6.7,
            )
        )
    }


@app.callback(
        Output('timeseries', 'figure'),
        [Input('filtered_data', 'children'),
         Input('mapbox_graph', 'hoverData'),
         Input('filteroptions', 'value'),
         ])
def timeseries_graph(jsonified_filtered_data, hoverdata, filteroptions):
    '''
    Builds timeseries graph. Uses hoverData to select camera point and filtered data from filter_data
    '''
    # Read input
    dff = pd.read_json(jsonified_filtered_data, orient='split')
    lat = np.round(hoverdata['points'][0]['lat'], 4)
    lon = np.round(hoverdata['points'][0]['lon'], 4)

    # Build timeseries for location
    timeseries_to_plot = dff[(dff['lat'] == lat) & (dff['lon'] == lon)].copy()
    if 'daily' in filteroptions:
        timeseries_to_plot.loc[:, 'hourly_timestamp'] = timeseries_to_plot['timestamp'].dt.hour
    else:
        timeseries_to_plot.loc[:, 'hourly_timestamp'] = timeseries_to_plot['timestamp'].apply(lambda dt: datetime.datetime(dt.year, dt.month, dt.day, dt.hour))
    timeseries_to_plot = timeseries_to_plot[['gevi', 'hourly_timestamp']]
    timeseries_to_plot = pd.get_dummies(timeseries_to_plot)
    timeseries_to_plot = timeseries_to_plot.groupby(timeseries_to_plot['hourly_timestamp']).sum()
    timeseries_to_plot.index.names = ['index']

    # store it as data variable for the plot
    data = [{'x': timeseries_to_plot.index, 'y':timeseries_to_plot[x], 'type': 'bar', 'name': x, 'showlegend': True} for x in timeseries_to_plot.columns]

    layout = dict(
                title='Tijdserie voor locatie %s, %s' % (lat, lon),
                plot_bgcolor="#1E1E1E", paper_bgcolor="#1E1E1E",
                font=dict(color="#d8d8d8"),
                xaxis=dict(title='Aantal vrachtwagens')
                )
    if 'daily' in filteroptions:
        layout['xaxis']['title'] = "Aantal vrachtwagens per uur"

    return {
        'data': data,
        'layout': layout
        }


app.run_server(debug=True)
