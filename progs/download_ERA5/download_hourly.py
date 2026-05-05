#!/usr/bin/env python3

import os
import cdsapi
import calendar

cal = calendar.Calendar( )
apiclient = cdsapi.Client( )

ys = 1979
ye = 2020

vname = {
	  'convective_rain_rate' : 'prc',
	  'surface_net_solar_radiation' : 'ssr',
	  'surface_thermal_radiation_downwards' : 'strd',
	  'total_precipitation' : 'pr',
	  '2m_temperature' : 'tas',
	  'mean_sea_level_pressure' : 'psl',
	  'total_cloud_cover' : 'clt',
          '10m_u_component_of_wind' : 'u10',
          '10m_v_component_of_wind' : 'v10',
          '100m_u_component_of_wind' : 'u100',
          '100m_v_component_of_wind' : 'v100',
        }

for year in range(ys,ye+1):
    yy = '%04d' % year
    for month in range(1,13):
        mm = '%02d' % month
        dlist = [ ]
        for d in cal.itermonthdays(year, month):
            if d > 0:
                dlist.append('%02d' % d)
        for var in vname.keys( ):
            netcdf = os.path.join('hourly',(vname[var]+"_"+yy+'_'+mm+'.nc'))
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
        'time':[ '00:00','01:00','02:00',
            '03:00','04:00','05:00',
            '06:00','07:00','08:00',
            '09:00','10:00','11:00',
            '12:00','13:00','14:00',
            '15:00','16:00','17:00',
            '18:00','19:00','20:00',
            '21:00','22:00','23:00' ],
    },
    netcdf)
                os.system('compressnc '+netcdf)
            else:
                print('File '+netcdf+' already on disk.')
