import requests
import pandas as pd
from datetime import datetime, timezone

# --- Config ---
image_service_url = "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN/ImageServer"
variable_name = "NO2_Troposphere"
coor_pts = "-117.0283, 32.5426"  # Coordenadas para Tijuana

# Constants for conversion
AVOGADRO = 6.022e23  # molecules/mol
MOLAR_MASS_NO2 = 46.0055  # g/mol
COLUMN_HEIGHT_M = 2000  # 2 km typical tropospheric column

def convert_to_ugm3(molec_per_cm2):
    """Converts molecule count per cm² to micrograms per cubic meter (µg/m³)."""
    if pd.isna(molec_per_cm2):
        return None
    molec_per_m2 = molec_per_cm2 * 1e4
    conc_molec_per_m3 = molec_per_m2 / COLUMN_HEIGHT_M
    conc_mol_per_m3 = conc_molec_per_m3 / AVOGADRO
    conc_g_per_m3 = conc_mol_per_m3 * MOLAR_MASS_NO2
    conc_ug_per_m3 = conc_g_per_m3 * 1e6
    return conc_ug_per_m3

# --- 1. Get available times ---
print("Fetching available timestamps from the server...")
dim_info_url = f"{image_service_url}/multidimensionalInfo"
dim_info = requests.get(dim_info_url, params={"f": "json"}).json()
all_times = dim_info["multidimensionalInfo"]["variables"][0]["dimensions"][0]["values"]
all_times.sort(reverse=True) # Sort from newest to oldest

# --- 2. Get the last 100 timestamps and create a time range ---
if not all_times:
    print("Error: No timestamps were found on the server.")
    exit()

# Get the most recent 100 timestamps
latest_100_times = all_times[:100]
print(f"Found {len(latest_100_times)} recent records to fetch.")

# The API accepts a range "startTime,endTime"
# The oldest time in our list is the start, the newest is the end.
time_range = f"{latest_100_times[-1]},{latest_100_times[0]}"

# --- 3. Fetch data for the entire time range ---
print(f"Requesting data for the time range: {time_range}")
params = {
    "geometry": coor_pts,
    "geometryType": "esriGeometryPoint",
    "returnFirstValueOnly": "false",
    "mosaicRule": f'{{"multidimensionalDefinition":[{{"variableName":"{variable_name}"}}]}}',
    "time": time_range,  # Use the time range here
    "f": "pjson",
}
response = requests.get(f"{image_service_url}/getSamples/", params=params)
data = response.json()

# --- 4. Process all returned samples ---
samples = []
for sample in data.get("samples", []):
    attributes = sample.get("attributes", {})
    var_value = attributes.get(variable_name)
    # The API might return text like 'NoData' for some points
    try:
        var_value_float = float(var_value)
        samples.append(
            {
                "StdTime": attributes["StdTime"],
                variable_name: var_value_float,
            }
        )
    except (ValueError, TypeError):
        # Skip records where the value is not a valid number
        continue

if not samples:
    print(f"No valid data found for {variable_name} at point ({coor_pts}) for the requested time range.")
else:
    df = pd.DataFrame(samples)
    df["StdTime"] = pd.to_datetime(df["StdTime"], unit="ms", utc=True)
    df = df.sort_values(by='StdTime', ascending=False) # Sort to show newest first

    # Apply the conversion to the entire column to create a new one
    df["NO₂_concentration_µg/m³"] = df[variable_name].apply(convert_to_ugm3)

    print("\n--- Last 100 Records ---")
    # Display the relevant columns, rounded for readability
    print(df[['StdTime', 'NO₂_concentration_µg/m³']].round(2))