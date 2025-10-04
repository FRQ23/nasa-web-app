import os
import requests
from getpass import getpass
from netrc import netrc
from platform import system
from subprocess import Popen

urs = "urs.earthdata.nasa.gov"  # Earthdata URL endpoint for authentication
prompts = ["Enter NASA Earthdata Login Username: ", "Enter NASA Earthdata Login Password: "]

# Determine the OS (Windows machines usually use an '_netrc' file)
netrc_name = "_netrc" if system() == "Windows" else ".netrc"
netrc_path = os.path.expanduser(f"~/{netrc_name}")  # <-- Guarda la ruta aquí

# Determine if netrc file exists, and if so, if it includes NASA Earthdata Login Credentials
try:
    netrc(netrc_path).authenticators(urs)[0]

# Below, create a netrc file and prompt user for NASA Earthdata Login Username and Password
except FileNotFoundError:
    homeDir = os.path.expanduser("~")
    Popen(
        "touch {0}{2} | echo machine {1} >> {0}{2}".format(homeDir + os.sep, urs, netrc_name),
        shell=True,
    )
    Popen(
        "echo login {} >> {}{}".format(getpass(prompt=prompts[0]), homeDir + os.sep, netrc_name),
        shell=True,
    )
    Popen(
        "echo 'password {} '>> {}{}".format(
            getpass(prompt=prompts[1]), homeDir + os.sep, netrc_name
        ),
        shell=True,
    )
    # Set restrictive permissions
    Popen("chmod 0600 {0}{1}".format(homeDir + os.sep, netrc_name), shell=True)

    # Determine OS and edit netrc file if it exists but is not set up for NASA Earthdata Login
except TypeError:
    homeDir = os.path.expanduser("~")
    Popen("echo machine {1} >> {0}{2}".format(homeDir + os.sep, urs, netrc_name), shell=True)
    Popen(
        "echo login {} >> {}{}".format(getpass(prompt=prompts[0]), homeDir + os.sep, netrc_name),
        shell=True,
    )
    Popen(
        "echo 'password {} '>> {}{}".format(
            getpass(prompt=prompts[1]), homeDir + os.sep, netrc_name
        ),
        shell=True,
    )

def search_collections(keyword, bbox, page_size=5):
    """Busca colecciones/datasets en CMR por palabra clave y bounding box."""
    url = "https://cmr.earthdata.nasa.gov/search/collections.json"
    params = {
        "keyword": keyword,
        "bounding_box": bbox,
        "page_size": page_size
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    results = resp.json()["feed"]["entry"]
    return results

def search_granules(collection_concept_id, bbox, page_size=5):
    """Busca archivos (granules) en una colección específica y bounding box."""
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "collection_concept_id": collection_concept_id,
        "bounding_box": bbox,
        "page_size": page_size
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    results = resp.json()["feed"]["entry"]
    return results

def download_file(url, dest):
    """Descarga un archivo usando autenticación .netrc."""
    # Usa netrc_path en vez de netrc() sin argumentos
    username, _, password = netrc(netrc_path).authenticators(urs)
    with requests.get(url, stream=True, auth=requests.auth.HTTPBasicAuth(username, password)) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def main():
    print("=== NASA Earthdata Dataset Downloader ===")
    # Bounding box para San Diego y Tijuana: [W,S,E,N]
    bbox = "-117.25,32.3,-116.8,32.7"
    keyword = input("Enter a keyword for dataset search (e.g. 'aerosol', 'temperature'): ")

    print("\nSearching datasets in San Diego/Tijuana area...")
    collections = search_collections(keyword, bbox)
    if not collections:
        print("No datasets found.")
        return

    print("\nAvailable datasets:")
    for idx, c in enumerate(collections):
        print(f"{idx+1}. {c.get('short_name')} - {c.get('summary', '')[:80]}...")

    sel = int(input("Select a dataset by number: ")) - 1
    collection_id = collections[sel]["id"]

    print("\nSearching available files (granules)...")
    granules = search_granules(collection_id, bbox)
    if not granules:
        print("No files found for this dataset in the area.")
        return

    print("\nAvailable files:")
    for idx, g in enumerate(granules):
        print(f"{idx+1}. {g.get('title')}")

    sel_g = int(input("Select a file to download by number: ")) - 1
    granule = granules[sel_g]
    links = [l["href"] for l in granule["links"] if l.get("rel", "").endswith("/data#") and "inherited" not in l]
    if not links:
        print("No downloadable link found.")
        return

    url = links[0]
    dest = os.path.basename(url)
    print(f"Downloading {dest} ...")
    download_file(url, dest)
    print("Download complete.")

if __name__ == "__main__":
    main()
