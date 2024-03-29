'''
Functions from the CBS3 truck visualization project
'''

import numpy as np
import matplotlib
import pandas as pd
from geopy.distance import distance

def get_color(intensity, max_intensity):
    ''' returns color value of colormap, depending on the ration between the
    intensity and the max intensity of the road. '''
    cmap = matplotlib.cm.get_cmap('YlOrBr')
    rgba = cmap(intensity/max_intensity)
    return 'rgb%s' %(str(rgba[:-1]))

def get_linewidth(intensity, max_intensity):
    ''' returns the rounded integer of a number between 2 and 10, depending on
    the ratio between the intensity and max intensity of the road'''
    return int(np.round(np.max([4.0, 10*(intensity/max_intensity)])))

def determine_bbox(zoom, center_lat, center_lon, fit):
    ''' returns coordinates of the bounding box of the visible graph.
    Scales with the zoom level and should be used to filter the data that
    has to be graphed'''
    boxdimensions = [800, 1200]  # size box in pixels [height,width]

    # determine distance per pixel
    distanceperpixel = fit(zoom)

    # distance of the box in meter
    verbox = boxdimensions[0]*distanceperpixel
    horbox = boxdimensions[1]*distanceperpixel

    # Determine the bounding coordinates
    maxlat = distance(meters=verbox/2).destination(
        (center_lat, center_lon), 0)[0]
    minlat = distance(meters=verbox/2).destination(
        (center_lat, center_lon), 180)[0]
    maxlon = distance(meters=horbox/2).destination(
        (center_lat, center_lon), 90)[1]
    minlon = distance(meters=horbox/2).destination(
        (center_lat, center_lon), 270)[1]
    return maxlat, maxlon, minlat, minlon

def read_input_csv(path, filename):
    '''
    Read csv from pat / filename
    '''
    df = pd.read_csv(str(path / filename))
    df = df.round(4)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Splitting bottom part of West into A4_R
    df.loc[(df['road'] == 'West') & (df['Camera_id'] < 7), 'road'] = 'A4'
    return df
