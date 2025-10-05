import requests
import pandas as pd
from datetime import datetime, timezone

# --- Config ---
image_service_url = "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN/ImageServer"
variable_name = "NO2_Troposphere"
coor_pts = "-117.0283, 32.5426"

# Constants for conversion
AVOGADRO = 6.022e23  # molecules/mol
MOLAR_MASS_HCHO = 30.026  # g/mol
COLUMN_HEIGHT_M = 2000  # 2 km typical tropospheric column

def convert_to_ugm3(molec_per_cm2):
    """Converts molecule count per cm² to micrograms per cubic meter (µg/m³)."""
    molec_per_m2 = molec_per_cm2 * 1e4
    conc_molec_per_m3 = molec_per_m2 / COLUMN_HEIGHT_M
    conc_mol_per_m3 = conc_molec_per_m3 / AVOGADRO
    conc_g_per_m3 = conc_mol_per_m3 * MOLAR_MASS_HCHO
    conc_ug_per_m3 = conc_g_per_m3 * 1e6
    return conc_ug_per_m3

# Update the variable name for Formaldehyde if needed
variable_name = "HCHO_Troposphere"  # Replace with the correct variable name for CH₂O


# --- Get available times ---
dim_info_url = f"{image_service_url}/multidimensionalInfo"
dim_info = requests.get(dim_info_url, params={"f": "json"}).json()
all_times = dim_info["multidimensionalInfo"]["variables"][0]["dimensions"][0]["values"]
all_times.sort(reverse=True)
latest_time = all_times[0]

# --- Fetch data for the latest time ---
params = {
    "geometry": coor_pts,
    "geometryType": "esriGeometryPoint",
    "returnFirstValueOnly": "false",
    "mosaicRule": f'{{"multidimensionalDefinition":[{{"variableName":"{variable_name}"}}]}}',
    "time": str(latest_time),
    "f": "pjson",
}
response = requests.get(f"{image_service_url}/getSamples/", params=params)
data = response.json()

samples = []
for sample in data.get("samples", []):
    attributes = sample.get("attributes", {})
    var_value = attributes.get(variable_name)
    if var_value:
        samples.append(
            {
                "StdTime": attributes["StdTime"],
                variable_name: float(var_value),
            }
        )

df = pd.DataFrame(samples)
if df.empty:
    print(f"No data found for {variable_name} at point ({coor_pts}) for the latest record.")
else:
    df["StdTime"] = pd.to_datetime(df["StdTime"], unit="ms", utc=True)
    df = df.sort_values(by='StdTime')
    latest_record = df.iloc[-1]
    no2_molec_cm2 = latest_record[variable_name]
    no2_ug_m3 = convert_to_ugm3(no2_molec_cm2)
    print("Latest record:")
    print(latest_record)
    print(f"\nNO₂ concentration (approximate, µg/m³): {no2_ug_m3:.2f}")
