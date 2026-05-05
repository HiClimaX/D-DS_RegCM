#!/usr/bin/env python3

import os
import cdsapi
import calendar

cal = calendar.Calendar( )
apiclient = cdsapi.Client( )

ys = 1979
ye = 2018

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
        for var in ( 'geopotential','specific_humidity','temperature',
            'u_component_of_wind','v_component_of_wind' ):
            netcdf = os.path.join(str(year),(vname[var]+"_"+yy+'_'+mm+'.nc'))
            if not os.path.isfile(netcdf):
                apiclient.retrieve(
    'reanalysis-era5-pressure-levels-monthly-means',
    {
        'product_type':'monthly_averaged_reanalysis',
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
        'time':[ '00:00']
    },
    netcdf)
                os.system('compressnc '+netcdf)
            else:
                print('File '+netcdf+' already on disk.')
