#%%
import geopandas as gpd
import fiona
from shapely.geometry import shape, mapping
import shapely as sp
import os,sys
from pathlib import Path
import numpy as np
import pandas as pd
import random
#%%
names = ['A1_T','A2_R','A15_T','A27_T','A28_T','West']
for name in names:
    # variable list:
    path = Path(r'C:\Users\rwsla\Lars\CBS_3_visualization') # Main directory
    nwb_dir = 'data/Wegvakken'
    #name = 'West'
    nwb_name = '%s.shp' %name
    output_dir = 'data/output'
    interpolate_per_x_m = 4000
    name_point_shapefile = '%s-points.shp' %name
    name_point_csv = '%s-points.csv' %name
    
    # Read NWB
    nwb = gpd.read_file(str(path / nwb_dir / nwb_name))
    
    # creation of the resulting shapefile
    schema = {'geometry': 'Point','properties': {'id': 'int'}}
    crs = nwb.crs
    
    with fiona.open(str(path / output_dir / name_point_shapefile), 'w', 'ESRI Shapefile', schema, crs=crs) as output:
        pointlistx = []
        pointlisty = []
        for i in np.arange(len(nwb)):
            geom = nwb.iloc[i,-1]
            # length of the LineString
            length = geom.length
            # creation of the resulting shapefile
            schema = {'geometry': 'Point','properties': {'id': 'int'}}
            # create points every 10 meters along the line
            for i, distance in enumerate(range(0, int(length), interpolate_per_x_m)):
                print(distance)
                point = geom.interpolate(distance)   
                output.write({'geometry':mapping(point),'properties': {'id':i}})
                
                pointlistx.append(point.bounds[0])
                pointlisty.append(point.bounds[1])
    pointdf = pd.DataFrame({
        'lon_RD' : pointlistx,
        'lat_RD' : pointlisty,
        'road' : name
    })
    
    pointdf.to_csv(str(path /output_dir/ name_point_csv))
        

#%% Read in all df's
df = pd.DataFrame()
for name in names:
    name_point_csv = '%s-points.csv' %name
    output_dir = 'data/output'
    
    df = pd.concat([df,pd.read_csv(str(path /output_dir/ name_point_csv),index_col=0)])

#%% Convert from RD to latlon
    
from pyproj import Proj, transform

inProj = Proj(init='epsg:28992')
outProj = Proj(init='epsg:4326')
def transformRD(row):
    x1 = row['lon_RD']
    y1 = row['lat_RD']
    x2,y2 = transform(inProj,outProj,x1,y1)
    return pd.Series([x2,y2])

df[['lon','lat']] = df.apply(transformRD,axis=1)

#%% 80kmh = 22.22 m/s --> 4000m in 180 seconden
random.seed(4)
gevis = ['33-1203','33-1090','66-1689','40-1334','23-1965','239-1001','33-1170','25-1070']
output_df = pd.DataFrame()
for hour in np.arange(24):
    print(hour)
    for minute in ['00','30']:
        name = random.choice(names)
        gevi = random.choice(gevis)
        print(name,gevi)
        temp_df = df[df['road']==name]
        
        timeseries = pd.date_range(start='2019-10-01 %s:%s:00' %(hour,minute), periods = len(temp_df),freq='3T')
        output_df = pd.concat([output_df,pd.DataFrame({'lat' : temp_df['lat'].values,
                                  'lon' : temp_df['lon'].values,
                                  'road' : name,
                                  'gevi' : gevi,
                                  'timestamp' : timeseries,
                                  })])
    
    

output_df.to_csv(str(path /output_dir/ 'proxy_data.csv'))
