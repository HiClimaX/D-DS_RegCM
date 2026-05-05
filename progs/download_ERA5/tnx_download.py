#!/usr/bin/env python3

import os
import cdsapi
import calendar
from random import randint
from time import sleep

cal = calendar.Calendar( )
#apiclient = cdsapi.Client( )

apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='0a57fa9b-7bac-4518-b649-b60efabd5257')
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='e2a0204e-0e92-4b63-960f-cfc542fbe951')  #Tung1
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='f552ae72-845f-4379-ac6b-0fead6b48675')  #Tung2
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='8be3bf25-d4c9-4029-80dd-f1ce769a8a38')  #Tung3

ys = 1991
ye = 1991

vname = { 'geopotential' : 'geop',
          'specific_humidity' : 'qhum',
          'temperature' : 'tatm',
          'u_component_of_wind' : 'uwnd',
          'v_component_of_wind' : 'vwnd' }

for year in range(ys,ye+1):
    yy = '%04d' % year
    try:
        os.mkdir(yy)
    except OSError:
        pass
    for month in range(1,13):
        mm = '%02d' % month
        dlist = [ ]
        for d in cal.itermonthdays(year, month):
            if d > 0:
                dlist.append('%02d' % d)
        for var in ( 'geopotential','specific_humidity','temperature',
            'u_component_of_wind','v_component_of_wind' ):
            netcdf = os.path.join(str(year),(vname[var]+"_"+yy+'_'+mm+'.nc'))
            if not os.path.isfile(netcdf):
                result = 0
                while result == 0:
                    try:
                        apiclient.retrieve(
    'reanalysis-era5-pressure-levels',
    {
        'product_type':'reanalysis',
        'format':'netcdf',
        'variable':[ var ],
        'pressure_level':[
            '1','2','3',
            '5','7','10',
            '20','30','50',
            '70','100','125',
            '150','175','200',
            '225','250','300',
            '350','400','450',
            '500','550','600',
            '650','700','750',
            '775','800','825',
            '850','875','900',
            '925','950','975',
            '1000'
        ],
        'year': yy,
        'month': mm,
        'day': dlist,
        'time':[ '00:00','06:00','12:00','18:00' ]
    },
    netcdf)
                        result = 1
                    except:
                        sleep(randint(10,100))
                        result = 0
                os.system('compressnc '+netcdf)
            else:
                print('File '+netcdf+' already on disk.')
