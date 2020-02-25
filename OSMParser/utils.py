#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 13:22:51 2019

@author: jhm
"""

import numpy as np
from pyproj import CRS, Transformer
from PIL import Image

crs_4326  = CRS.from_epsg(4326) # epsg 4326 is wgs84
crs_25832  = CRS.from_epsg(25832) # epsg 25832 is etrs89
transformer = Transformer.from_crs(crs_4326, crs_25832)


def giveHeading(x1,y1,x2,y2):
        x = [x1,x2]
        y = [y1,y2]
        x_arr=np.array(x)-x[0]
        y_arr=np.array(y)-y[0]
        #rotate to initial approximately 0
        #umrechnen in polarkoordinaten des ersten abstandes
        if x_arr[1] > 0:
                    phi = np.arctan(y_arr[1]/x_arr[1])
        elif x_arr[1] == 0:
                    if y_arr[1] > 0:
                            phi = np.pi/2
                    else:
                            phi = -np.pi/2
        else:
                    if y_arr[1] >= 0:
                            phi = np.arctan(y_arr[1]/x_arr[1])+np.pi
                    else:
                            phi = np.arctan(y_arr[1]/x_arr[1])-np.pi
        return phi


def checkDistance(x,y,x2,y2):
    x_m = (x+x2)/2.0
    y_m = (y+y2)/2.0
    r = ((x_m-x)**2+(y_m-y)**2)**0.5
    [_,_],phi,_,_ = rotateToXAxis([x_m,x2],[y_m,y2])
    return x_m, y_m, r, phi

def getCurves(xTriplett,yTriplett, r=5):
    [x3,y3],phi,x_arr,y_arr = rotateToXAxis(xTriplett,yTriplett)
    x2 = x_arr[-2]
    y2 = y_arr[-2]
    x_arr -= x_arr[-2]
    y_arr -= y_arr[-2]
    #print([x2,y2])
    #   get theta
    if x_arr[-1] > 0:
                            theta = np.arctan(y_arr[-1]/x_arr[-1])
    elif x_arr[-1] == 0:
                            if y_arr[-1] > 0:
                                    theta = np.pi/2
                            else:
                                    theta = -np.pi/2
    else:
                            if y_arr[-1] >= 0:
                                    theta = np.arctan(y_arr[-1]/x_arr[-1])+np.pi
                            else:
                                    theta = np.arctan(y_arr[-1]/x_arr[-1])-np.pi
    # move points at theta/2 --> all points in x Order and S_1 = -S_2
    theta = -theta/2.0
    x_arr, y_arr = drehen(x_arr,y_arr,theta,drehpunkt = [x_arr[1],y_arr[1]]) 
    # get Parameter
    if x_arr[-1] != 0.0:
        S = y_arr[-1]/x_arr[-1]
    else:
        S = 9999.9
        print("x_arr[-1] = 0.0 --> U-turn?")
        print(xTriplett)
        print(yTriplett)
        print(" ")
    r = min(r, checkDistance(x_arr[0],y_arr[0],x_arr[1],y_arr[1])[2], checkDistance(x_arr[2],y_arr[2],x_arr[1],y_arr[1])[2] )
    x_t = (r**2/(1+S**2))**0.5
    c = S/(2*x_t)
    if c > 500:
        print("Sanity check --> U-Turn?")
        print("x: " + str(xTriplett))
        print("y: "+str(yTriplett))
        print(c)
        c = 9
        #1/0
    # b = Sx_t - x c_t²
    b = S*x_t - (c*x_t**2)
    x_t_arr = np.linspace(-x_t,x_t,num=15)
    y_t_arr = c*x_t_arr**2 +b
    length = 0.0
    oldx = x_t_arr[0]
    oldy = y_t_arr[0]
    for i in range(len(x_t_arr)):
            length += ((x_t_arr[i]-oldx)**2+(y_t_arr[i]-oldy)**2)**0.5
            oldx = x_t_arr[i]
            oldy = y_t_arr[i]
    length = length/2.0   

    #turn back
    x_t_arr, y_t_arr = drehen(x_t_arr, y_t_arr,-theta,drehpunkt = [x_arr[1],y_arr[1]],offset=True)
    x_arr, y_arr = drehen(x_arr, y_arr,-theta,drehpunkt = [x_arr[1],y_arr[1]],offset=True)

    x_t_arr += x2
    x_arr += x2
    y_t_arr += y2
    y_arr += y2

    x_t_arr, y_t_arr = drehen(x_t_arr, y_t_arr,-phi)
    x_arr, y_arr = drehen(x_arr, y_arr,-phi)

    x_t_arr += x3
    x_arr += x3
    y_t_arr += y3
    y_arr += y3
    
    line1x = [x_arr[0],x_t_arr[0]]
    line1y = [y_arr[0],y_t_arr[0]]
    line2x = [x_t_arr[-1],x_arr[-1]]
    line2y = [y_t_arr[-1], y_arr[-1]]
    #C1  <-
    #C2 ->
    C1Heading = (-phi-theta+np.pi)%(2*np.pi)
    C1start = [x_t_arr[7],y_t_arr[7]]
    C2start = [x_t_arr[7],y_t_arr[7]]
    C2Heading = (0-phi-theta)%(2*np.pi)
    C1params = [0,0,-c,0]
    C2params = [0,0,c,0]

    return line1x,line1y, -phi, C1start,C1params[2], C1Heading, length, C2start,C2params[2], C2Heading, line2x,line2y,2*theta

    #return [line1x,line1y], -phi, [C1start,C1params], C1Heading, length, [C2start,C2params], C2Heading, [line2x,line2y],2*theta

def drehen(x,y,phi, drehpunkt = [0,0], offset = False):
        x = np.array(x)-drehpunkt[0]
        y = np.array(y)-drehpunkt[1]
        dmat =  np.array([[np.cos(phi),-np.sin(phi)],[np.sin(phi),np.cos(phi)]])
        x_new = []
        y_new = []
        for i in range(len(x)):
            points = np.matmul(dmat,np.hstack((x[i],y[i])))
            x_new.append(points[0])
            y_new.append(points[1])
        x_new = np.array(x_new)
        y_new = np.array(y_new)
        if offset:
            x_new = x_new+drehpunkt[0]
            y_new = y_new+drehpunkt[1]
        return x_new, y_new

def rotateToXAxis(x,y):
        x_arr=np.array(x)-x[0]
        y_arr=np.array(y)-y[0]
        #rotate to initial approximately 0
        #umrechnen in polarkoordinaten des ersten abstandes
        if x_arr[1] > 0:
                    phi = np.arctan(y_arr[1]/x_arr[1])
        elif x_arr[1] == 0:
                    if y_arr[1] > 0:
                            phi = np.pi/2
                    else:
                            phi = -np.pi/2
        else:
                    if y_arr[1] >= 0:
                            phi = np.arctan(y_arr[1]/x_arr[1])+np.pi
                    else:
                            phi = np.arctan(y_arr[1]/x_arr[1])-np.pi
        phi = -phi
        x_arr,y_arr = drehen(x_arr,y_arr,phi)
        return [x[0],y[0]],phi,x_arr,y_arr
    
global referenceLat
global referenceLon
referenceLat = None
referenceLon = None


global topoParameter
global topomap
def convertTopoMap(topomappath, osmpath):
        global topomap
        global topoParameter
        topomap =  np.array(Image.open(topomappath))[:,:,0] #y,x,rgba
        topoParameter = giveMaxMinLongLat(osmpath)
        return topoParameter
        
def giveHeight(x,y):
        try:
                global topoParameter
                global topomap
                x_lookup= int(topomap.shape[1]*(x-topoParameter[0])/(topoParameter[1]-topoParameter[0]))
                y_lookup = int(topomap.shape[0]*(y-topoParameter[2])/(topoParameter[3]-topoParameter[2]))
                x_lookup = max(0,min(topomap.shape[1]-1,x_lookup))
                y_lookup = max(0,min(topomap.shape[0]-1,y_lookup))
                return topomap[y_lookup,x_lookup]
        except:
                return 0.0

def giveMaxMinLongLat(osmpath):
        minlat = 0
        maxlat = 0
        minlon = 0
        maxlon = 0
        with open(osmpath, "r") as f:
                for line in f:
                        if "minlat='" in line:
                               minlat = float(line.split("minlat='")[1].split("'")[0])
                        if "maxlat='" in line:
                               maxlat = float(line.split("maxlat='")[1].split("'")[0])
                        if "maxlon='" in line:
                               maxlon = float(line.split("maxlon='")[1].split("'")[0])
                        if "minlon='" in line:
                               minlon = float(line.split("minlon='")[1].split("'")[0])
                        if 'minlat="' in line:
                               minlat = float(line.split('minlat="')[1].split('"')[0])
                        if 'maxlat="' in line:
                               maxlat = float(line.split('maxlat="')[1].split('"')[0])
                        if 'maxlon="' in line:
                               maxlon = float(line.split('maxlon="')[1].split('"')[0])
                        if 'minlon="' in line:
                               minlon = float(line.split('minlon="')[1].split('"')[0])
                xmin,ymin = convertLongitudeLatitude(minlon,minlat)
                xmax,ymax = convertLongitudeLatitude(maxlon,maxlat)
                return xmin, xmax, ymin, ymax

def convertLongitudeLatitude(longitude,latitude):
        #return longitude, latitude
        global referenceLat
        global referenceLon

        x,y = next(transformer.itransform([(latitude,longitude)]))

        '''if referenceLat is None:
            referenceLat = latitude
            referenceLon = longitude
        x = (latitude - referenceLat)*150000
        y = (longitude - referenceLon)*150000'''
        return x,y
    
