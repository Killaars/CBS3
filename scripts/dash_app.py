#%%
'''
TODO
#- Zelfde vrachtwagen minder vaak meetellen
# --> gemiddelde per punt
- buttons etc op de goede plek
- Bootstrap components
- Resetten of niet na actie
- stresstest
#- verschillende zooms
#--> van segment naar wegniveau
#--> linkerbaan/rechterbaan
- Naar CSS kijken
- Alleen data in graph bekijken. Hoge zoom niveaus dus alleen lokale data
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
path = Path('/home/killaarsl/Documents/CBS3_visualization/') # Main directory

# Read csv file
df = pd.read_csv(str(path / 'data/output/proxy_data.csv'))
df = df.round(4)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Splitting bottom part of West into A4_R
df.loc[(df['road']=='West')&(df['Camera_id']<7),'road']='A4'

road_lats = [df[df['road']==x][['Camera_id','lat']].sort_values(by='Camera_id').drop_duplicates(subset='Camera_id')['lat'].values for x in df['road'].unique()]
road_lons = [df[df['road']==x][['Camera_id','lon']].sort_values(by='Camera_id').drop_duplicates(subset='Camera_id')['lon'].values for x in df['road'].unique()]
road_points = pd.DataFrame({'lats' : road_lats,
                            'lons' : road_lons},index = df['road'].unique())

# Create df with number of cameras for the entire road
nr_cameras = pd.DataFrame({'nr_cameras' : [len(df[df['road']==x]['Camera_id'].unique()) for x in df['road'].unique()]},
                                           index = df['road'].unique())

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
                                value = 23
                                )
                        
                        ],
                        style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    
            ]),
        html.Div([
                dcc.Graph(id='mapbox_graph', 
                          hoverData={'points': [{'lat': 52.3128,'lon' : 7.0391}]},
                          relayoutData={'mapbox.zoom': 6.5},
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
     Input('mapbox_graph','relayoutData'),
     ])
def update_figure(jsonified_filtered_data,relayoutData):
    '''
    Builds mapbox graph graph. Uses filtered data from filter_data.
    Calculates intensity for the road pieces and determines color and linewidth based on this
    '''

    # Add default zoom if not present in relayoutData
    if 'mapbox.zoom' not in relayoutData:
        relayoutData['mapbox.zoom']=6.5
    print(relayoutData)
    
    # Load data from hidden div
    dff = pd.read_json(jsonified_filtered_data, orient='split')
    
    # Zoom smaller than XXXX --> aggregates per road. Segment and travel direction in hoverinfo
    if relayoutData['mapbox.zoom'] < 8:
        # If one or more entries, fill plot_data graph, else, return empty trace
        if len(dff)>0:
            # Bepalen max_intensity of all roads
            max_intensity = max(dff['road'].value_counts()/nr_cameras['nr_cameras'])    
            
            # Bepalen intensiteit per road
            plot_data = []
            for road in dff['road'].unique():
                intensity = len(dff[dff['road']==road])/nr_cameras.loc[road,'nr_cameras']   
                plot_data.append(dict(type='scattermapbox',
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
    
    # Zoom smaller than XXXX --> aggregates per segment. Travel direction in hoverinfo
    if relayoutData['mapbox.zoom'] >= 8:
        # Determine maximum intensity for each segment
        # first for each travel direction
        max_intensity = []
        for direction in dff['direction'].unique():
            temp_df = dff[dff['direction']==direction]
            max_intensity.append(max([max(temp_df[temp_df['road']==x]['Camera_id'].value_counts()) for x in temp_df['road'].unique()]))
        max_intensity = max(max_intensity)
        
        # Empty plot data
        plot_data = []
        
        for direction in dff['direction'].unique():
            temp_df = dff[dff['direction']==direction]
            for road in temp_df['road'].unique():
                for segment in temp_df[temp_df['road']==road]['Camera_id'].unique():
                    intensity = len(temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment)])
                    
                    # Select coords of this point and the next, if not possible, only this point
                    try:
                        lats = [temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment)]['lat'].mean(),
                                    temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment+1)]['lat'].mean()]
                        lons = [temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment)]['lon'].mean(),
                                    temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment+1)]['lon'].mean()]
                    except:
                        lats = [temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment)]['lat'].mean()]
                        lons = [temp_df[(temp_df['road']==road)&(temp_df['Camera_id']==segment)]['lon'].mean()]
                        
                    plot_data.append(dict(type='scattermapbox',
                                      lat = lats,
                                      lon = lons,
                                      mode='lines',
                                      text='%s - %s - %s' %(intensity,road,direction),
                                      line=dict(width=get_linewidth(intensity,max_intensity),
                                                color=get_color(intensity,max_intensity)),
                                      showlegend=False,
                                      name=road,
                                      hoverinfo='text'
                                      ))            
    
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
                uirevision='no reset of zoom',
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
    # Read input
    dff = pd.read_json(jsonified_filtered_data, orient='split')
    lat = np.round(hoverData['points'][0]['lat'],4)
    lon = np.round(hoverData['points'][0]['lon'],4)
    
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
                'title': 'Timeseries for location %s, %s' %(lat,lon)
                }
            }
                                    
app.run_server(debug=True)
