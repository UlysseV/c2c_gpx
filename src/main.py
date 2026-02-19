import argparse
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
from urllib.parse import urlparse, parse_qs


requests_cache.install_cache(
    "c2c_cache", backend="sqlite", expire_after=timedelta(days=1)
)

# converts GPS coords from Web Mercator (3857) to WGS84 (4326)
transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

# Base URL for the C2C API
API_BASE_URL = "https://api.camptocamp.org"
BASE_URL = "https://www.camptocamp.org/routes"

delay = 0.5

headers = {"User-Agent": "C2C-GPX-Exporter-User"}

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

    def repl_l(m: Any) -> str:
        nonlocal count_l
        count_l += 1
        return f"<b>L{count_l}</b>"

    def repl_r(m: Any) -> str:
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

def get_locale(route: dict[str, Any], lang: str="fr") -> dict[str, Any] | None:
    for loc in route["locales"]:
        if loc["lang"] == lang:
            assert isinstance(loc, dict)
            return loc
    return None

def get_locales(route: dict[str, Any], langs: list[str]=["fr", "en"]) -> dict[str, Any]:
    for lang in langs:
        if loc := get_locale(route, lang):
            return loc
    raise RuntimeError(f"route {route['document_id']} has no locale in {langs}")

def format_route_description(route_data: dict[str, Any]) -> str:
    route_id = route_data["document_id"]
    desc = get_locales(route_data)
    # title = desc["title"]
    title_prefix = desc.get("title_prefix")
    summary = desc.get("summary")
    route_history = desc.get("route_history")
    description = desc.get("description")
    remarks = desc.get("remarks")
    gear = desc.get("gear")

    lines = [f'<p> <a href="{BASE_URL}/{route_id}">{route_id}</a>']

    if title_prefix:
        lines.append(f"<b>Secteur</b> : {title_prefix}")

    if cotation := create_route_grade(route_data):
        lines.append(f"<b>Cotations</b> : {cotation}")

    if altitude := create_route_altitude(route_data):
        lines.append(f"<b>Altitude</b> : {altitude}")

    if orientation := create_route_orientation(route_data):
        lines.append(f"<b>Orientation</b> : {orientation}")
    # TODO: use compass rose image for orientation ?

    if height := create_route_height(route_data):
        lines.append(f"<b>Dénivelé</b> : {height}")
        
    # TODO: add rock type (limestone, sandstone), climbing type (multi-pitch, bloc,...)

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
    return body


def get_document_coord(document_data: dict[str, Any]) -> tuple[float, float]:
    x, y = json.loads(document_data["geometry"]["geom"])["coordinates"]
    lon, lat = transformer.transform(x, y)
    assert isinstance(lon, float)
    assert isinstance(lat, float)
    return lon, lat


def get_default_description(doc_type: str, document_data: dict[str, Any]) -> str:
    document_id = document_data["document_id"]
    desc = get_locales(document_data)

    lines = [f'<p> <a href="{BASE_URL}/{doc_type}/{document_id}">{doc_type.strip("s")} #{document_id}</a></p>']

    for k, v in desc.items():
        if k in ("title", "lang", "version", "topic_id") or not v:
            continue
                    
        content = clean_and_html(v) if isinstance(v, str) else v
        lines.append(f"<b>{k}</b></br>{content}")
    body = "<br/>".join(lines)
    return body
    
    

def get_document_description(doc_type: str, document_data: dict[str, Any]) -> str:
    if doc_type == "routes":
        return format_route_description(document_data)
    
    return get_default_description(doc_type, document_data)
    


def create_document_waypoint(doc_type: str, document_data: dict[str, Any]) -> gpxpy.gpx.GPXWaypoint:
    """Create a GPX waypoint from any document type."""
    loc = get_locales(document_data)
    title = loc["title"]
    lon, lat = get_document_coord(document_data)
    wp = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=title)
    
    description = get_document_description(doc_type, document_data)
    wp.description = description
    
    # TODO: use other attributes ?
    # wp.comment
    # wp.symbol
    # wp.elevation
    # wp.link
    
    return wp


def get_document_data(doc_type: str, document_id: int) -> dict[str, Any]:
    url = f"{API_BASE_URL}/{doc_type}/{document_id}"
    response = requests.get(url)
    if not getattr(response, "from_cache", False):
        time.sleep(delay)
    response_json = response.json()
    assert isinstance(response_json, dict)
    return response_json


def get_documents_data(doc_type: str, document_ids: list[int]) -> dict[int, dict[str, Any]]:
    documents_data: dict[int, dict[str, Any]] = dict()
    for doc_id in tqdm.tqdm(document_ids, total=len(document_ids)):
        documents_data[doc_id] = get_document_data(doc_type, doc_id)
    return documents_data


def build_gpx(doc_type: str, documents_data: dict[int, dict[str, Any]]) -> gpxpy.gpx.GPX:
    gpx = gpxpy.gpx.GPX()
    for doc_data in documents_data.values():
        wp = create_document_waypoint(doc_type, doc_data)
        gpx.waypoints.append(wp)

    return gpx


def save_gpx(gpx: gpxpy.gpx.GPX, name: str) -> None:
    with open(name, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    print(f"file {name} created with {len(gpx.waypoints)} waypoints")


def parse_c2c_url(url: str) -> tuple[str, dict[str, Any]]:
    """
    Parse a camptocamp.org search URL and extract the document type and API parameters.
    
    Returns a tuple of (document_type, params).
    Supported document types: routes, outings, waypoints, xreports
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Extract the document type from the URL path
    doc_type = parsed.path.strip("/")

    # Pass all query parameters directly to the API (convert lists to single values)
    params: dict[str, Any] = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
    
    # Set limit to the max value (reduces queries due to pagination)
    params["limit"] = 100
    
    return doc_type, params


def get_document_ids(doc_type: str, params: dict[str, Any]) -> list[int]:
    """Get document IDs based on the document type and search parameters."""
    url = f"{API_BASE_URL}/{doc_type}"
    output: list[int] = []
    offset = 0
    while True:
        search_params = {**params, "offset": offset}
        response = requests.get(url, params=search_params, headers=headers)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        documents = data["documents"]
        # TODO: compare len(documents) to data["total"] for breaking
        if len(documents) == 0:
            break
        offset += len(documents)
        output.extend(d["document_id"] for d in documents)
    return output


def generate_filename(doc_type: str, params: dict[str, Any]) -> str:
    """Generate a filename based on document type and search parameters."""
    parts = [doc_type]
    for k, v in params.items():
        v = str(v).replace(",", "-")
        parts.append(f"{k}-{v}")
    return "_".join(parts) + ".gpx"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export camptocamp.org documents (routes, outings, waypoints, xreports) to GPX format"
    )
    parser.add_argument(
        "url",
        type=str,
        help="Camptocamp.org search URL (e.g., https://www.camptocamp.org/routes?act=rock_climbing&bbox=616096,5333945,627309,5346461)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output GPX filename (default: auto-generated based on params)",
    )
    args = parser.parse_args()
    
    # Parse the URL to get document type and API params
    doc_type, params = parse_c2c_url(args.url)
    
    print(f"Fetching {doc_type}...")
    document_ids = get_document_ids(doc_type, params)
    documents_data = get_documents_data(doc_type, document_ids)
    gpx = build_gpx(doc_type, documents_data)
    
    # Determine output filename
    if args.output:
        filename = args.output if os.path.isabs(args.output) else os.path.join(export_folder, args.output)
    else:
        default_filename = generate_filename(doc_type, params)
        filename = os.path.join(export_folder, default_filename)
    
    save_gpx(gpx, filename)


if __name__ == "__main__":
    main()
