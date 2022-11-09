import pandas as pd
import os
import argparse
import configparser
import numpy as np
import time
import statistics
import math
import cmath
import json
import rdp
import matplotlib.pyplot as plt
from math import radians, cos, sin, asin, sqrt, floor
from random import choices
from scipy.fft import fft, ifft
import warnings; warnings.simplefilter('ignore')

def norm_data(data):
    """
    normalize data to have mean=0 and standard_deviation=1
    """
    mean_data=np.mean(data)
    std_data=np.std(data, ddof=1)
    #return (data-mean_data)/(std_data*np.sqrt(data.size-1))
    return (data-mean_data)/(std_data)

def ncc(data0, data1):
    """
    normalized cross-correlation coefficient between two data sets
    Parameters
    ----------
    data0, data1 :  numpy arrays of same size
    """
    return (1.0/(data0.size-1)) * np.sum(norm_data(data0)*norm_data(data1))


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    All args must be of equal length.
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2

    c = 2 * np.arcsin(np.sqrt(a))
    m = 6367000 * c
    return m

def distance(x):
    y = x.shift()
    return haversine_np(x['longitude'], x['latitude'], y['longitude'], y['latitude']).fillna(0)

def addwatermark(watermark, df_2, lp):
    # lp = int(config['global']['slice'])
    lat_array = df_2[['latitude', 'longitude']].values
    c = []
    for i in range(lp):
        c.append(complex(lat_array[i][0], lat_array[i][1]))

    x1 = fft(c)
    magnitude = x1.real
    p = 0.0003
    new_magnitude = np.zeros(lp)
    for j in range(lp):
        new_magnitude[j] = magnitude[j] + (p * watermark[j])
    formed_signal = []
    for k in range(lp):
        z = complex(new_magnitude[k], x1[k].imag)
        formed_signal.append(z)
    watermarked_signal = np.fft.ifft(formed_signal)
    df_watermarked = pd.DataFrame(watermarked_signal.real, columns=['watermarked_lat'])
    df_watermarked['watermarked_long'] = watermarked_signal.imag
    frame = [df_2, df_watermarked]
    final_df = pd.concat(frame, axis=1)
    return final_df, x1

def is_unitary(m):
    return np.allclose(np.eye(m.shape[0]), m.H * m)

def watermarkExtract(df_wc,x1_org,lp, col_lat, col_long):
    # lp=int(config['global']['slice'])
    watermarked_array = df_wc[[col_lat, col_long]].values
    c_w = []
    for l in range(lp):
        c_w.append(complex(watermarked_array[l][0], watermarked_array[l][1]))

    p = 0.0003
    fourier_wc = fft(c_w)
    extract_wc = np.zeros(lp)
    for m in range(lp):
        vl = (((fourier_wc[m].real - x1_org[m].real)) / p)
        extract_wc[m]=vl
    return extract_wc

def prepare_output_trip_file(input_file_path, output_file_path, watermarked_df):
    with open(input_file_path, 'r') as f:
        trips_data_dict_original = json.load(f)
    lst_lst_coords = watermarked_df[['watermarked_lat', 'watermarked_long']].values.tolist()
    for i in range(len(trips_data_dict_original['data'])):
        if trips_data_dict_original['data'][i]['metric_id'] == '6587929f-e425-498b-b450-aa615851400b':
            trips_data_dict_original['data'][i]['values'] = lst_lst_coords
    f.close()
    # writing the updated dict to a new output file which will now have watermarked coordinates
    watermarked_file = open(output_file_path, "w")
    json.dump(trips_data_dict_original, watermarked_file, indent=10)
    watermarked_file.close()

    

