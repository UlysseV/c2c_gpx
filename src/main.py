from datetime import timedelta
from pyproj import Transformer
from typing import Any
import gpxpy
import gpxpy.gpx
import json
import markdown
import os
import re
import requests
import requests_cache
import time
import tqdm


# TODO: check that this does something (which I presently doubt)
requests_cache.install_cache(
    "c2c_cache", backend="sqlite", expire_after=timedelta(days=1)
)

# converts GPS coords from Web Mercator (3857) to WGS84 (4326)
transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

# todo: enable base urls for outings, accidents, etc.
base_url = "https://www.camptocamp.org/routes"
search_url = "https://api.camptocamp.org/routes"

# TODO: pass as a parameter
params = {
    "act": "rock_climbing",
    "bbox": "616096,5333945,627309,5346461",  # Cap Canaille
    # "bbox": "600371,5336634,616327,5353833",  # Calanques
    "frat": "2,6b",
    "rrat": "2,6a",
    "qa": "draft,great",
    "limit": 100,
}

delay = 0.5

headers = {"User-Agent": "C2C-GPX-Exporter-User"}

# route_keys = {
#     "elevation_min": "Altitude min",
#     "elevation_max": "Altitude max",
#     "height_diff_up": "Dénivelé positif",
#     "height_diff_down": "Dénivelé négatif",
#     "durations": "Durée",
#     "calculated_duration": "Durée calculée",
#     "height_diff_difficulties": "Dénivelé des difficultés",
#     "orientations": "Orientation",
#     "global_rating": "Cotation globale",
#     "engagement_rating": "Engagement",
#     "risk_rating": "Risque",
#     "equipment_rating": "Équipement",
#     "exposition_rock_rating": "Exposition",
#     "rock_free_rating": "Cotation libre",
#     "rock_required_rating": "Cotation obligatoire",
#     "aid_rating": "Cotation artificielle",
#     "climbing_outdoor_type": "Type d'escalade",
#     "public_transportation_rating": "Transports publiques",
# }

export_folder = "exports"


def create_route_grade(route: dict[str, Any]) -> str:
    gradings = ""
    if global_rating := route.get("global_rating"):
        gradings += global_rating
    if rock_free_rating := route.get("rock_free_rating"):
        gradings += " " + rock_free_rating
    if rock_required_rating := route.get("rock_required_rating"):
        gradings += ">" + rock_required_rating
    if aid_rating := route.get("aid_rating"):
        gradings += " " + aid_rating
    if engagement_rating := route.get("engagement_rating"):
        gradings += " " + engagement_rating
    if risk_rating := route.get("risk_rating"):
        gradings += " " + risk_rating
    if equipment_rating := route.get("equipment_rating"):
        gradings += " " + equipment_rating
    if exposition_rock_rating := route.get("exposition_rock_rating"):
        gradings += " " + exposition_rock_rating
    return gradings.strip()


def create_route_altitude(route: dict[str, Any]) -> str:
    e = []
    if elevation_min := route["elevation_min"]:
        e.append(f"{elevation_min} m")
    if elevation_max := route["elevation_max"]:
        e.append(f"{elevation_max} m")

    return " - ".join(e)


def create_route_orientation(route: dict[str, Any]) -> str:
    if orientation := route["orientations"]:
        return ",".join(orientation)
    return ""


def create_route_height(route: dict[str, Any]) -> str:
    e = []
    if height_diff_up := route["height_diff_up"]:
        e.append(f"+{height_diff_up} m")
    if height_diff_down := route["height_diff_down"]:
        e.append(f"-{height_diff_down} m")

    height_diff_difficulties = route["height_diff_difficulties"]

    if height_diff_difficulties:
        if not e:
            return f"{height_diff_difficulties} m"
        return " / ".join(e) + f" ({height_diff_difficulties} m)"

    return " / ".join(e)


def increment_pitches(text: str) -> str:
    count_l, count_r = 0, 0

    def repl_l(m):
        nonlocal count_l
        count_l += 1
        return f"<b>L{count_l}</b>"

    def repl_r(m):
        nonlocal count_r
        count_r += 1
        return f"<b>R{count_r}</b>"

    # handle numberless pitches
    text = text.replace(r"L#~", "")
    text = text.replace(r"R#~", "")
    
    # handle already numbered pitches
    text = re.sub(r"L#(\d+)", r"<b>L\1</b>", text)
    text = re.sub(r"R#(\d+)", r"<b>R\1</b>", text)
    
    text = re.sub(r"L#", repl_l, text)
    text = re.sub(r"R#", repl_r, text)
    return text


def clean_and_html(text: str) -> str:
    # replace C2C links with HTML ones
    text = re.sub(
        r"\[\[(routes|waypoints|outings|articles|images)/(\d+)(?:\|(.*?))?\]\]",
        lambda m: (
            f'<a href="https://www.camptocamp.org/{m.group(1)}/{m.group(2)}">{m.group(3) if m.group(3) else m.group(1) + " " + m.group(2)}</a>'
        ),
        text,
    )
    
    # replace image ref
    text = re.sub(
        r'\[img=(\d+).*?\](.*?)\[/img\]',
        # r'<div style="font-size:0.9em; color:#666;"><img src="https://media.camptocamp.org/c2corg-active/uploads/images/\1.jpg" style="width:100%;"><br>📸 \2</div>',
        r'<a href="https://media.camptocamp.org/c2corg-active/uploads/images/\1.jpg">[📸 \2]</a>',
        text
    )
    
    text = text.replace("|", "<td>")

    text = increment_pitches(text)
    html = markdown.markdown(text, extensions=["nl2br", "sane_lists", "tables"])
    return html

def get_locale(route, lang="fr") -> dict[str, Any] | None:
    for loc in route["locales"]:
        if loc["lang"] == lang:
            return loc
    return None

def get_locales(route, langs=["fr", "en"]) -> dict[str, Any]:
    for lang in langs:
        if loc := get_locale(route, lang):
            return loc
    raise RuntimeError(f"route {route['document_id']} has no locale in {langs}")

def create_route_info(route: dict[str, Any]) -> tuple[str, str]:
    route_id = route["document_id"]
    desc = get_locales(route)
    title = desc["title"]
    title_prefix = desc.get("title_prefix")
    summary = desc.get("summary")
    route_history = desc.get("route_history")
    description = desc.get("description")
    remarks = desc.get("remarks")
    gear = desc.get("gear")

    lines = [f'<p> <a href="{base_url}/{route_id}">{route_id}</a>']

    if title_prefix:
        lines.append(f"<b>Secteur</b> : {title_prefix}")

    if cotation := create_route_grade(route):
        lines.append(f"<b>Cotations</b> : {cotation}")

    if altitude := create_route_altitude(route):
        lines.append(f"<b>Altitude</b> : {altitude}")

    if orientation := create_route_orientation(route):
        lines.append(f"<b>Orientation</b> : {orientation}")
    # TODO: use image for orientation ?

    if height := create_route_height(route):
        lines.append(f"<b>Dénivelé</b> : {height}")
        
    # TODO: rock type (limestone, sandstone), climbing type (multi-pitch, bloc,...)

    if summary is not None:
        lines.append(clean_and_html(summary))
    lines.append('</p>')
    
    lines.append('<hr>')
    
    if route_history is not None:
        lines.append(
            f"<h1>Historique</h1> {clean_and_html(route_history)}"
        )
    if description is not None:
        lines.append(f"<h1>Description</h1> {clean_and_html(description)}")
    if remarks is not None:
        lines.append(f"<h1>Remarques</h1> {clean_and_html(remarks)}")
    if gear is not None:
        lines.append(f"<h1>Équipement</h1> {clean_and_html(gear)}")

    body = "<br/>".join(lines)
    return title, body


def get_route_coord(route: dict[str, Any]) -> tuple[float, float]:
    x, y = json.loads(route["geometry"]["geom"])["coordinates"]
    return transformer.transform(x, y)


def create_route_waypoint(route: dict[str, Any]) -> gpxpy.gpx.GPXWaypoint:
    # take the first language available, TODO: select fr > en > fail !
    title, desc = create_route_info(route)
    lon, lat = get_route_coord(route)
    wp = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=title)
    wp.description = desc
    # wp.comment = f""
    return wp


def get_route_ids(params: dict[str, Any]) -> list[int]:
    output: list[int] = []
    offset = 0
    while True:
        params["offset"] = offset
        response = requests.get(search_url, params=params, headers=headers)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        routes = data["documents"]  # TODO: sqlite validation
        if len(routes) == 0:
            break
        offset += len(routes)
        output.extend(r["document_id"] for r in routes)

    return output


def get_route_data(route_id):
    response = requests.get(f"{search_url}/{route_id}").json()
    if not getattr(response, "from_cache", False):
        time.sleep(delay)
    return response


def build_gpx(route_ids: list[int]):

    routes_data = []
    for rid in tqdm.tqdm(route_ids, total=len(route_ids)):
        routes_data.append(get_route_data(rid))

    gpx = gpxpy.gpx.GPX()
    for route_data in routes_data:
        wp = create_route_waypoint(route_data)
        gpx.waypoints.append(wp)

    return gpx


def save_gpx(gpx, name):
    with open(os.path.join(export_folder, name), "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    print(f"file {name} created with {len(gpx.waypoints)} waypoints")


if __name__ == "__main__":
    route_ids = get_route_ids(params)
    gpx = build_gpx(route_ids)
    save_gpx(gpx, "climbing_routes.gpx")
