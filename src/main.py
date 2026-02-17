import requests_cache
from datetime import timedelta

requests_cache.install_cache(
    'c2c_cache', 
    backend='sqlite', 
    expire_after=timedelta(days=1)
)
import requests
import gpxpy
import gpxpy.gpx
from typing import Any
import json

from pyproj import Transformer

# converts GPS coords from Web Mercator (3857) to WGS84 (4326)
transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

base_url = "https://www.camptocamp.org/routes"
search_url = "https://api.camptocamp.org/routes"
params = {
    "act": "rock_climbing",
    "bbox": "616096,5333945,627309,5346461",  # cap canaille
    "frat": "2,6b",
    "rrat": "2,6a",
    "qa": "draft,great",
    "limit": 100,
}

headers = {"User-Agent": "C2C-GPX-Exporter-User"}

route_keys = {
    "elevation_min": "Altitude min",
    "elevation_max": "Altitude max",
    "height_diff_up": "Dénivelé positif",
    "height_diff_down": "Dénivelé négatif",
    "durations": "Durée",
    "calculated_duration": "Durée calculée",
    "height_diff_difficulties": "Dénivelé des difficultés",
    "orientations": "Orientation",
    "global_rating": "Cotation globale",
    "engagement_rating": "Engagement",
    "risk_rating": "Risque",
    "equipment_rating": "Équipement",
    "exposition_rock_rating": "Exposition",
    "rock_free_rating": "Cotation libre",
    "rock_required_rating": "Cotation obligatoire",
    "aid_rating": "Cotation artificielle",
    "climbing_outdoor_type": "Type d'escalade",
    "public_transportation_rating": "Transports publiques",
}

def download_routes() -> None:
    response = requests.get(search_url, params=params, headers=headers)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    print(f"fetched {data['total']} routes")
    routes = data['documents']
    assert len(routes) == data['total']
    
    gpx = gpxpy.gpx.GPX()
    
    for route in routes:
        # if "fr" not in route["available_langs"]:
        #     continue
        # desc = [loc for loc in route["locales"] if loc["lang"] == "fr"][0]
        desc = route["locales"][0]
        
        title = desc.get("title", "N/A")
        title_prefix = desc.get("title_prefix", "N/A")
        summary = desc.get("summary", "N/A")
        route_id = route["document_id"]
        metadata = [
            f"{title_prefix} : {title}\n"
            f"{base_url}/{route_id}\n"
        ]
        for k,n in route_keys.items():
            v = route.get(k)
            if not v:
                continue
            metadata.append(f"{n} : {v}")
        metadata.append(f"Description : {summary}")
        
        x, y = json.loads(route["geometry"]["geom"])["coordinates"]
        lon, lat = transformer.transform(x, y)
        wp = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=title)
        wp.description = "\n".join(metadata)
        # wp.comment = f""
        gpx.waypoints.append(wp)

    with open("voies_climbing.gpx", "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    
    print(f"file created with {len(gpx.waypoints)} waypoints.")

if __name__ == "__main__":
    download_routes()