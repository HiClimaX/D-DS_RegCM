#!/usr/bin/env python3

import os
import cdsapi
import calendar

cal = calendar.Calendar( )

#apiclient = cdsapi.Client( )
apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='0a57fa9b-7bac-4518-b649-b60efabd5257')
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='e2a0204e-0e92-4b63-960f-cfc542fbe951')  #Tung1
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='f552ae72-845f-4379-ac6b-0fead6b48675')  #Tung2
#apiclient = cdsapi.Client(url = 'https://cds.climate.copernicus.eu/api', key='8be3bf25-d4c9-4029-80dd-f1ce769a8a38')  #Tung3

ys = 1979
ye = 2018

vname = { 'sea_surface_temperature' : 'sst' }

for year in range(ys,ye+1):
    yy = '%04d' % year
    try:
        os.mkdir('SST')
    except OSError:
        pass
    for month in range(1,13):
        mm = '%02d' % month
        dlist = [ ]
        for d in cal.itermonthdays(year, month):
            if d > 0:
                dlist.append('%02d' % d)
        var = 'sea_surface_temperature'
        netcdf = os.path.join('SST',(vname[var]+"_"+yy+'_'+mm+'.nc'))
        if not os.path.isfile(netcdf):
            apiclient.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type':'reanalysis',
        'format':'netcdf',
        'variable':[ var ],
        'year': yy,
        'month': mm,
        'day': dlist,
        'time':[ '00:00','06:00','12:00','18:00' ]
    },
    netcdf)
            os.system('compressnc '+netcdf)
        else:
            print('File '+netcdf+' already on disk.')
