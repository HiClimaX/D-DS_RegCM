import os
import cdsapi
import calendar
import shutil
from random import randint
from time import sleep

# --- CONFIGURATION ---
BASE_DRIVE_PATH = '/content/drive/MyDrive/ERA5_Data'
os.makedirs(BASE_DRIVE_PATH, exist_ok=True)

ys, ye = 1991, 1991
vname = { 
    'geopotential': 'geop',
    'specific_humidity': 'qhum',
    'temperature': 'tatm',
    'u_component_of_wind': 'uwnd',
    'v_component_of_wind': 'vwnd' 
}

cal = calendar.Calendar()
apiclient = cdsapi.Client()

for year in range(ys, ye + 1):
    yy = '%04d' % year
    year_dir = os.path.join(BASE_DRIVE_PATH, yy)
    os.makedirs(year_dir, exist_ok=True)
    
    for month in range(1, 13):
        mm = '%02d' % month
        dlist = [f'{d:02d}' for d in cal.itermonthdays(year, month) if d > 0]
        
        for var in vname.keys():
            filename = f"{vname[var]}_{yy}_{mm}.nc"
            drive_path = os.path.join(year_dir, filename)
            local_temp_path = os.path.join('/content', filename) # Local Colab disk (fast)

            # 1. CHECK IF FILE EXISTS ON DRIVE
            if os.path.exists(drive_path):
                # Optional: Check if the file is suspiciously small (e.g., < 100 bytes)
                if os.path.getsize(drive_path) > 1024: 
                    print(f"✅ Skipping {filename} (Already exists on Drive)")
                    continue
                else:
                    print(f"⚠️ Found corrupted file for {filename}, re-downloading...")
                    os.remove(drive_path)

            print(f"🚀 Requesting {var} for {yy}-{mm}...")
            
            success = False
            while not success:
                try:
                    # 2. DOWNLOAD TO LOCAL DISK FIRST
                    apiclient.retrieve(
                        'reanalysis-era5-pressure-levels',
                        {
                            'product_type': 'reanalysis',
                            'format': 'netcdf',
                            'variable': [var],
                            'pressure_level': [
                                '1','2','3','5','7','10','20','30','50','70','100',
                                '125','150','175','200','225','250','300','350','400',
                                '450','500','550','600','650','700','750','775','800',
                                '825','850','875','900','925','950','975','1000'
                            ],
                            'year': yy,
                            'month': mm,
                            'day': dlist,
                            'time': ['00:00', '06:00', '12:00', '18:00']
                        },
                        local_temp_path)
                    
                    # 3. COMPRESSION (Optional - requires !apt install nco)
                    # os.system(f'ncks -4 -L 1 {local_temp_path} {local_temp_path}.compressed && mv {local_temp_path}.compressed {local_temp_path}')
                    
                    # 4. MOVE COMPLETED FILE TO DRIVE
                    shutil.move(local_temp_path, drive_path)
                    print(f"⭐ Successfully saved {filename} to Drive.")
                    success = True
                    
                except Exception as e:
                    print(f"❌ Error: {e}. Retrying in 30 seconds...")
                    # Cleanup local temp file if it exists to avoid disk clutter
                    if os.path.exists(local_temp_path):
                        os.remove(local_temp_path)
                    sleep(30)
