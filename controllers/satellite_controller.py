import traceback

from flask import jsonify, request
import ee
import datetime

from models.satellite_model import get_s2_collection
from utils.helpers import validate_date_range
from utils.logger import logger


# -------------------- HEALTH -------------------- #

def health_check():
    return jsonify({"status": "ok"})


def api_health():
    try:
        size = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .limit(1)
            .size()
            .getInfo()
        )
        return jsonify({
            "status": "ok",
            "earth_engine": "connected",
            "test_collection_size": size,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(e)
        return jsonify({"status": "error", "message": str(e)}), 500


# -------------------- COMPOSITE -------------------- #

def composite():
    # ✅ CORS preflight
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json() or {}

        geometry = data.get("geometry")
        start_date = data.get("start_date", "2017-06-23")
        end_date = data.get(
            "end_date",
            datetime.datetime.now().strftime("%Y-%m-%d")
        )
        max_cloud = float(data.get("max_cloud", 30))
        index_type = data.get("index_type", "NDVI").upper()
        scale = int(data.get("scale", 10))

        if not geometry:
            return jsonify({"success": False, "error": "Missing geometry"}), 400

        if not validate_date_range(start_date, end_date):
            return jsonify({"success": False, "error": "Invalid date range"}), 400

        geom = ee.Geometry(geometry).buffer(50)
        collection = get_s2_collection(geom, start_date, end_date, max_cloud)

        count = collection.size().getInfo()
        if count == 0:
            return jsonify({"success": False, "error": "No images found"}), 404

        base_image = collection.median().clip(geom)

        if index_type == "NDVI":
            index_image = base_image.select("NDVI")
            vis_params = {"min": -1, "max": 1, "palette": ["#0000ff", "#ffffff", "#00ff00"]}
        elif index_type == "NDWI":
            index_image = base_image.select("NDWI")
            vis_params = {"min": -1, "max": 1, "palette": ["#8b4513", "#ffffff", "#0000ff"]}
        elif index_type == "NSMI":
            index_image = base_image.select("NSMI")
            vis_params = {"min": -1, "max": 1, "palette": ["#ffff00", "#ffffff", "#ff0000"]}
        elif index_type == "TRUE_COLOR":
            index_image = base_image.select(["B4", "B3", "B2"])
            vis_params = {"min": 0, "max": 3000}
        else:
            return jsonify({"success": False, "error": "Invalid index_type"}), 400

        map_id = ee.Image(index_image).getMapId(vis_params)
        download_url = ee.Image(index_image).getDownloadURL({
            "scale": scale,
            "region": geom,
            "fileFormat": "GeoTIFF",
            "formatOptions": {"cloudOptimized": True}
        })

        return jsonify({
            "success": True,
            "index_type": index_type,
            "image_count": count,
            "tile_url": map_id["tile_fetcher"].url_format,
            "download_url": download_url,
            "vis_params": vis_params,
            "date_range": f"{start_date} to {end_date}",
            "scale": scale
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------- TIME SERIES -------------------- #
# -------------------- TIME SERIES -------------------- #

def compute_derivatives(values):
    """
    values: list of floats
    returns: first_derivative, second_derivative
    """
    first = [None]
    for i in range(1, len(values)):
        first.append(values[i] - values[i - 1])

    second = [None, None]
    for i in range(2, len(values)):
        second.append(first[i] - first[i - 1])

    return first, second


def timeseries():

    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json() or {}

        point = data.get("point", {})
        lat = point.get("lat")
        lng = point.get("lng")
        ranges = data.get("ranges", [])
        max_cloud = float(data.get("max_cloud", 30))

        if lat is None or lng is None:
            return jsonify({
                "success": False,
                "error": "Missing latitude or longitude"
            }), 400

        if not ranges or len(ranges) < 1:
            return jsonify({
                "success": False,
                "error": "At least one date range required"
            }), 400

        lat = float(lat)
        lng = float(lng)

        geom = ee.Geometry.Point([lng, lat])

        all_results = []

        for range_obj in ranges:

            start_date = range_obj.get("start_date")
            end_date = range_obj.get("end_date")

            if not validate_date_range(start_date, end_date):
                continue

            collection = get_s2_collection(
                geom, start_date, end_date, max_cloud
            )

            collection = collection.sort(
                "CLOUDY_PIXEL_PERCENTAGE"
            ).limit(150)

            def extract(img):
                stats = img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom.buffer(20),
                    scale=10,
                    maxPixels=1e9
                )

                return ee.Feature(None, {
                    "date": img.date().format("YYYY-MM-dd"),
                    "NDVI": stats.get("NDVI"),
                    "NDWI": stats.get("NDWI"),
                    "NSMI": stats.get("NSMI")
                })

            fc = ee.FeatureCollection(collection.map(extract)).getInfo()

            series = []

            for f in fc.get("features", []):
                props = f.get("properties", {})

                if props.get("NDVI") is None:
                    continue

                series.append({
                    "date": props.get("date"),
                    "NDVI": round(float(props["NDVI"]), 4) if props.get("NDVI") else None,
                    "NDWI": round(float(props["NDWI"]), 4) if props.get("NDWI") else None,
                    "NSMI": round(float(props["NSMI"]), 4) if props.get("NSMI") else None
                })

            series.sort(key=lambda x: x["date"])

            all_results.append({
                "range": f"{start_date} to {end_date}",
                "data": series
            })

        return jsonify({
            "success": True,
            "ranges": all_results
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500