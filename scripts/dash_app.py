#%%
'''
TODO
- Zelfde vrachtwagen minder vaak meetellen
- buttons etc op de goede plek
- linkerbaan rechterbaan?
'''
#%%
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
import datetime

from variables import token

# Read shapefile
path = Path('/mnt/74C6E433C6E3F2F2/Users/rwsla/Lars/CBS_3_visualization/') # Main directory
shp_dir = 'data/output'
shp_name = 'all6_4326.geojson'

# Read csv file
df = pd.read_csv(str(path / 'data/output/proxy_data.csv'))
df.rename(columns={"Unnamed: 0": "Camera_id"},inplace=True)
df = df.round(4)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Splitting bottom part of West into A4_R
df.loc[(df['road']=='West')&(df['Camera_id']<7),'road']='A4_R'


road_lats = [df[df['road']==x][['Camera_id','lat']].sort_values(by='Camera_id').drop_duplicates(subset='Camera_id')['lat'].values for x in df['road'].unique()]
road_lons = [df[df['road']==x][['Camera_id','lon']].sort_values(by='Camera_id').drop_duplicates(subset='Camera_id')['lon'].values for x in df['road'].unique()]
road_points = pd.DataFrame({'lats' : road_lats,
                            'lons' : road_lons},index = df['road'].unique())

# Get first and last timestamp, in order to get first and last dates and times
mn, mx = min(df['timestamp']),max(df['timestamp'])

# Kleuren/lijndiktes/teksten afhankelijk van de intensiteit
def get_color(intensity,max_intensity):
    ''' returns color value of colormap, depending on the ration between the 
    intensity and the max intensity of the road. '''
    cmap = matplotlib.cm.get_cmap('YlOrBr')
    rgba = cmap(intensity/max_intensity)
    return 'rgb%s' %(str(rgba[:-1]))

def get_linewidth(intensity,max_intensity):
    ''' returns the rounded integer of a number between 2 and 10, depending on 
    the ratio between the intensity and max intensity of the road'''
    return int(np.round(np.max([4.0,10*(intensity/max_intensity)])))


## Wegen afhankelijk van de zoom
#

#%%
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']                          
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
        html.Div([
                html.Div([
                        dcc.RadioItems(
                                id='mode',
                                options=[{'label': i, 'value': i} for i in ['Realtime', 'Aggregated']],
                                value='Realtime',
                                labelStyle={'display': 'inline-block'}),
                        dcc.Dropdown(
                                id='gevi_selector',
                                options=[{'label': i, 'value': i} for i in df['gevi'].unique()],
                                multi=True,
                                value = [])
                        ],
                        style={'width': '48%', 'display': 'inline-block'}),
                html.Div([
                        dcc.DatePickerRange(
                                id='date_picker',
                                start_date = datetime.datetime(mn.year,mn.month,mn.day),
                                end_date = datetime.datetime(mx.year,mx.month,mx.day),
                                ),
                        dcc.Dropdown(
                                id='begin_time',
                                options=[{'label': i, 'value': i} for i in range(24)],
                                value = 0
                                ),
                        dcc.Dropdown(
                                id='end_time',
                                options=[{'label': i, 'value': i} for i in range(24)],
                                value = 0
                                )
                        
                        ],
                        style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    
            ]),
        html.Div([
                dcc.Graph(id='mapbox_graph', 
                          hoverData={'points': [{'lat': 52.3128}]}
                          )],
                          style={'width': '69%','display': 'inline-block', 'padding': '0 20'}
                ),
        html.Div([
                dcc.Graph(id='timeseries')],
                style={'display': 'inline-block', 'width': '29%'}
                ),
    # Hidden div inside the app that stores the intermediate value
    html.Div(id='filtered_data', style={'display': 'none'})
    ])

### Filter data callback
'''
Filters and stores the df as json, other graphs can use it as input
'''
@app.callback(
    Output('filtered_data', 'children'),
    [Input('mode', 'value'),
     Input('gevi_selector', 'value'),
     Input('date_picker', 'start_date'),
     Input('date_picker', 'end_date'),
     Input('begin_time', 'value'),
     Input('end_time', 'value'),
     ])
def filter_data(selected_mode,selected_gevi,start_date,end_date,begin_time,end_time):
    ######### Realtime 
    '''
    TODO Change to 15 minutes before now
    '''
    if selected_mode == 'Realtime':
        timecutoff = max(df['timestamp']) - datetime.timedelta(minutes=15)
        filtered_df = df[df['timestamp']>=timecutoff]
        
    ######### Aggregated
    if selected_mode == 'Aggregated':
        
        ###### filter dates
        start = str(pd.to_datetime(start_date) + pd.to_timedelta(int(begin_time), unit='h')) ## Type start_date is string?
        end = str(pd.to_datetime(end_date) + pd.to_timedelta(int(end_time), unit='h'))
        
        filtered_df = df[(df['timestamp']>=start)&(df['timestamp']<=end)]
    
    # Filter gevi codes based on selection    
    if len(selected_gevi)>0:
        filtered_df = filtered_df[filtered_df['gevi'].isin(selected_gevi)]
    else:
        filtered_df = filtered_df
        
    return filtered_df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('mapbox_graph', 'figure'),
    [Input('filtered_data', 'children'),
     ])
def update_figure(jsonified_filtered_data):
    '''
    Builds mapbox graph graph. Uses filtered data from filter_data.
    Calculates intensity for the road pieces and determines color and linewidth based on this
    '''
    dff = pd.read_json(jsonified_filtered_data, orient='split')
    
    ########## If one or more entries, fill plot_data graph, else, return empty trace
    if len(dff)>0:
        # Bepalen max_intensity of all roads
        max_intensity = max(dff['road'].value_counts())    
        
        # Bepalen intensiteit per segment
        plot_data = []
        for road in dff.road.unique():
            intensity = len(dff[dff['road']==road])    
            plot_data.append(dict(type='scattermapbox',
                                  #lat = dff[dff['road']==road]['lat'].unique(),
                                  #lon = dff[dff['road']==road]['lon'].unique(),
                                  lat = road_points.loc[road,'lats'],
                                  lon = road_points.loc[road,'lons'],
                                  mode='lines',
                                  text=str(intensity),
                                  line=dict(width=get_linewidth(intensity,max_intensity),
                                            color=get_color(intensity,max_intensity)),
                                  showlegend=True,
                                  name=road,
                                  hoverinfo='text'
                                  ))
    else:
        plot_data = []
    
    ### Returns plot_data as data part of plotly graph and filled layout 
    return {
        "data":plot_data,
        "layout": dict(
            #autosize = True,
            height = 800,
            legend = dict(orientation="h"),
            hovermode = "closest",
            margin = dict(l = 0, r = 0, t = 0, b = 0),
            #margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
            mapbox = dict(
                accesstoken = token,
                #bearing = 0,
                center = dict(
                          lon=5.104480, 
                          lat=52.092876),
                style = "light",
                #pitch = 0,
                zoom = 6.5,
            )
        )
    }
                                      
@app.callback(
        Output('timeseries','figure'),
        [Input('filtered_data', 'children'),
         Input('mapbox_graph','hoverData'),
         ])
def timeseries_graph(jsonified_filtered_data,hoverData):
    '''
    Builds timeseries graph. Uses hoverData to select camera point and filtered data from filter_data
    '''
    print(hoverData)
    # Read input
    dff = pd.read_json(jsonified_filtered_data, orient='split')
    lat = hoverData['points'][0]['lat']
    
    # Build timeseries for location
    #print(lat,dff['lat'].unique())
    timeseries_to_plot = dff[dff['lat']==lat].copy()
    timeseries_to_plot.loc[:,'hourly_timestamp'] = timeseries_to_plot['timestamp'].apply(lambda dt: datetime.datetime(dt.year, dt.month, dt.day, dt.hour))
    timeseries_to_plot = timeseries_to_plot[['gevi','hourly_timestamp']]
    timeseries_to_plot = pd.get_dummies(timeseries_to_plot)
    timeseries_to_plot = timeseries_to_plot.groupby(timeseries_to_plot['hourly_timestamp']).sum()
    timeseries_to_plot.index.names = ['index']
    #print(timeseries_to_plot)
    # store it as data variable for the plot
    data = [{'x': timeseries_to_plot.index,'y':timeseries_to_plot[x],'type':'bar','name':x, 'showlegend':True} for x in timeseries_to_plot.columns]
    
    return {
            'data': data,
            'layout': {
                'title': 'Timeseries for location %s' %(lat)
                }
            }
                                    
app.run_server(debug=True)