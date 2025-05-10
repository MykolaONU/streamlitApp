import re
import pandas as pd
from PyPDF2 import PdfReader
import numpy as np

def hhmm_to_timedelta(col):
    return pd.to_timedelta(col.str.extract(r'(\d{4})')[0].str[:2] + ":" + col.str.extract(r'(\d{4})')[0].str[2:] + ":00")

def parse_solar_coordinates(coord):
    # Regular expression to extract latitude, longitude, and Carrington longitude
    match = re.match(r'([NS])(\d+)([EW])(\d+)(L\d+)', coord)
    
    if match:
        # Extract latitude and adjust for hemisphere
        lat_hemisphere = match.group(1)  # S or N
        lat_degree = int(match.group(2))  # 12
        
        # Extract longitude and adjust for hemisphere
        lon_hemisphere = match.group(3)  # E or W
        lon_degree = int(match.group(4))  # 46
        
        # Extract Carrington longitude (L)
        longitude_part = match.group(5)  # L170
        carrington_longitude = int(longitude_part[1:])  # remove 'L' and convert
        
        # Apply hemispheres (negative for South and West)
        latitude = -lat_degree if lat_hemisphere == 'S' else lat_degree
        longitude = lon_degree if lon_hemisphere == 'E' else -lon_degree


        # Возвращаем значения с полушариями
        lat_hemisphere_name = 'S' if lat_hemisphere == 'S' else 'N'
        lon_hemisphere_name = 'W' if lon_hemisphere == 'W' else 'E'
        

        return latitude, longitude, carrington_longitude, lat_hemisphere_name, lon_hemisphere_name
    else:
        return  np.nan, np.nan, np.nan

def parse_flare_df(df):
    # Шаблон для парсинга данных с возможным отсутствием важности и яркости
    df = df.replace("М", "M").replace("Х", "X")
    if '/' in df:
        # Разделяем по дефису, ожидая, что класс и важность местами перепутаны
        parts = df.split('/')
        if len(parts) == 2 and re.match(r'([1234SF])([NF|B]*)', parts[0]) and re.match(r'[A-X]\d+(\.\d+)?', parts[1]):
            df = parts[1] + '/' + parts[0]  # Меняем местами
        
    match = re.match(r'([A-X])([><]?\d+(\.\d+)?)(/([1234SF])?(N|F|B)?)?', df)
    
    if match:
        x_ray_class = match.group(1)  # Например, 'X'
        peak_flux = float(match.group(2).lstrip('><'))  # Например, 2.6
        
        # Важность (если есть)
        importance_code = match.group(5)  # Например, '1', 'S' или пусто
        brightness_code = match.group(6)  # Например, 'N', 'F', 'B' или пусто
        
        # Определе
        # Определение важности по площади, если есть информация о важности
        if importance_code in ['S', '1', '2', '3', '4']:
            importance_map = {
                'S': 'Subflare (area < 2.1 deg²)',
                '1': 'Importance 1 (2.1 < area < 5.1 deg²)',
                '2': 'Importance 2 (5.2 < area < 12.4 deg²)',
                '3': 'Importance 3 (12.5 < area < 24.7 deg²)',
                '4': 'Importance 4 (area > 24.8 deg²)'
            }
            importance_str = importance_map.get(importance_code, 'Unknown Importance')
        else:
            importance_str = 'No Importance Provided'
        
        # Яркость вспышки, если указана
        if brightness_code in ['N', 'F', 'B']:
            brightness_map = {
                'N': 'Normal',
                'F': 'Faint',
                'B': 'Brilliant'
            }
            brightness_str = brightness_map.get(brightness_code, 'Unknown Brightness')
        else:
            brightness_str = 'No Brightness Provided'
        
        # Возвращаем результаты
        return x_ray_class, peak_flux, importance_str, brightness_str
    else:
        return np.nan

def addColumns(df):
    df['date'] = pd.to_datetime(df['ymd'], format='%Y%m%d')
    
    # Convert to timedelta
    df['toTime'] = hhmm_to_timedelta(df['to'])
    df['teTime'] = hhmm_to_timedelta(df['te'])
    df['tmTime'] = hhmm_to_timedelta(df['tm']).apply(
        lambda x: f"{int(x.total_seconds() // 3600):02d}:{int((x.total_seconds() % 3600) // 60):02d}"
        if pd.notnull(x) else None
    )

    # Adjust for midnight crossing
    df['teTime'] = df.apply(lambda row: row['teTime'] + pd.Timedelta(hours=24) if row['teTime'] < row['toTime'] else row['teTime'], axis=1)

    # Calculate duration
    df['duration'] = df['teTime'] - df['toTime']

    # Convert duration to total minutes (optional)
    df['duration_minutes'] = df['duration'].dt.total_seconds() / 60

    # Convert duration to HH:MM format (optional)
    df['duration_hhmm'] = df['duration'].apply(
        lambda x: f"{int(x.total_seconds() // 3600):02d}:{int((x.total_seconds() % 3600) // 60):02d}"
        if pd.notnull(x) else None
    )
    df['toTime'] = df['toTime'].apply(
        lambda x: f"{int(x.total_seconds() // 3600):02d}:{int((x.total_seconds() % 3600) // 60):02d}"
        if pd.notnull(x) else None
    )

    df['teTime'] = df['teTime'].apply(
        lambda x: f"{int(x.total_seconds() // 3600):02d}:{int((x.total_seconds() % 3600) // 60):02d}"
        if pd.notnull(x) else None
    )
    # Convert to uppercase
    df['coord'] = df['coord'].str.upper()
    df[['lat', 'lon', 'carrington_Lon', 'lat_hemisphere', 'lon_hemisphere']] = df['coord'].apply(
        lambda x: pd.Series(parse_solar_coordinates(x))
    )

    df[['x_ray_class', 'peak_flux', 'importance', 'brightness']] = df['xray/opt'].apply(
        lambda x: pd.Series(parse_flare_df(x))
    )
    df['L'] = pd.to_numeric(df['L'], errors='coerce')

    return df
