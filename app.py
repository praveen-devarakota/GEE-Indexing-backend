from flask import Flask, jsonify, request
from flask_cors import CORS
import ee
import datetime
import os
import logging

# -------------------- Logging -------------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Flask App -------------------- #
app = Flask(__name__)
CORS(app)

# -------------------- Earth Engine Init -------------------- #
# Set these in your environment or hard-code locally (DO NOT hard-code in public repos)
SERVICE_ACCOUNT = os.getenv("GEE_SERVICE_ACCOUNT", "praveen88@flask-backend-478306.iam.gserviceaccount.com")
KEY_FILE = os.getenv("GEE_KEY_FILE", "gee-api.json")  # path to your JSON key on server

try:
    credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE)
    ee.Initialize(credentials)
    logger.info("Google Earth Engine initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Earth Engine: {e}")
    raise RuntimeError(f"Error initializing Earth Engine: {e}")

# -------------------- Utility Functions -------------------- #

def validate_date_range(start_date, end_date):
    try:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        return start_dt < end_dt
    except ValueError:
        return False


def mask_s2_clouds(image):
    """
    Cloud masking using Sentinel-2 Scene Classification Layer (SCL).
    Keeps:
      2 = Dark area pixels
      4 = Vegetation
      5 = Bare soils
      6 = Water
      11 = Snow and ice (optional, you can remove)
    Masks out clouds, shadows, etc.
    """
    scl = image.select("SCL")

    good = (
        scl.eq(2)
        .Or(scl.eq(4))
        .Or(scl.eq(5))
        .Or(scl.eq(6))
        .Or(scl.eq(11))
    )

    return image.updateMask(good).copyProperties(image, image.propertyNames())


def add_indices(image):
    """
    Add NDVI, NDWI, NSMI bands to the image.
    NDVI = (B8 - B4) / (B8 + B4)
    NDWI = (B3 - B8) / (B3 + B8)
    NSMI = (B8 - B11) / (B8 + B11)
    """
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
    nsmi = image.normalizedDifference(["B8", "B11"]).rename("NSMI")

    return image.addBands([ndvi, ndwi, nsmi])


def get_s2_collection(geom, start_date, end_date, max_cloud=30):
    """
    Build a cloud-masked, index-added Sentinel-2 collection.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
        .map(mask_s2_clouds)
        .map(add_indices)
    )
    return collection


# -------------------- Routes -------------------- #

@app.route("/api/health", methods=["GET"])
def health():
    try:
        size = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").limit(1).size().getInfo()
        return jsonify({
            "status": "ok",
            "earth_engine": "connected",
            "test_collection_size": size,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/composite", methods=["POST"])
def composite():
    """
    Build a composite for a given geometry and return:
      - Tile URL for frontend visualization
      - Download URL (GeoTIFF) for the whole AOI (full map, not just one tile)
      - Index type (NDVI, NDWI, NSMI or TRUE_COLOR)
    """
    try:
        data = request.get_json()
        geometry = data.get("geometry")
        start_date = data.get("start_date", "2017-06-23")
        end_date = data.get("end_date", datetime.datetime.now().strftime("%Y-%m-%d"))
        max_cloud = float(data.get("max_cloud", 30))
        index_type = data.get("index_type", "NDVI").upper()
        scale = int(data.get("scale", 10))  # meters

        if not geometry:
            return jsonify({"success": False, "error": "Missing geometry"}), 400

        if not validate_date_range(start_date, end_date):
            return jsonify({"success": False, "error": "Invalid date range"}), 400

        geom = ee.Geometry(geometry).buffer(50)

        collection = get_s2_collection(geom, start_date, end_date, max_cloud)
        count = collection.size().getInfo()

        if count == 0:
            return jsonify({"success": False, "error": "No images found for given parameters"}), 404

        logger.info(f"Composite request: {count} images in collection")

        # Use median composite for more stable result
        base_image = collection.median().clip(geom)

        # Visualization + index selection
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
            # True color composite
            index_image = base_image.select(["B4", "B3", "B2"])
            vis_params = {"min": 0, "max": 3000}
        else:
            return jsonify({"success": False, "error": "Invalid index_type"}), 400

        # Tile URL for map visualization
        map_id = ee.Image(index_image).getMapId(vis_params)
        tile_url = map_id["tile_fetcher"].url_format

        # Download URL for full AOI GeoTIFF (whole Sentinel-2 map over region)
        download_url = ee.Image(index_image).getDownloadURL({
            "scale": scale,
            "region": geom,
            "fileFormat": "GeoTIFF",
            "formatOptions": {
                "cloudOptimized": True
            }
        })

        return jsonify({
            "success": True,
            "index_type": index_type,
            "image_count": count,
            "tile_url": tile_url,
            "download_url": download_url,
            "vis_params": vis_params,
            "date_range": f"{start_date} to {end_date}",
            "scale": scale
        })

    except Exception as e:
        logger.error(f"Error in /api/composite: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/timeseries", methods=["POST"])
def timeseries():
    """
    Extract NDVI/NDWI/NSMI time-series for a given point.
    Body:
      {
        "point": { "lat": ..., "lng": ... },
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "max_cloud": 30
      }
    """
    try:
        data = request.get_json()

        point_data = data.get("point", {})
        lat = float(point_data.get("lat"))
        lng = float(point_data.get("lng"))

        start_date = data.get("start_date", "2017-06-23")
        end_date = data.get("end_date", datetime.datetime.now().strftime("%Y-%m-%d"))
        max_cloud = float(data.get("max_cloud", 30))

        if not validate_date_range(start_date, end_date):
            return jsonify({"success": False, "error": "Invalid date range"}), 400

        point = ee.Geometry.Point([lng, lat])

        collection = get_s2_collection(point, start_date, end_date, max_cloud)

        count = collection.size().getInfo()
        if count == 0:
            return jsonify({"success": False, "error": "No images found"}), 404

        logger.info(f"Timeseries request: {count} images")

        def extract_values(img):
            # mean values over a small buffer around the point
            region = point.buffer(20).bounds()
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=10,
                maxPixels=1e9
            )
            return ee.Feature(None, {
                "date": img.date().format("YYYY-MM-dd"),
                "NDVI": stats.get("NDVI"),
                "NDWI": stats.get("NDWI"),
                "NSMI": stats.get("NSMI"),
                "cloud_cover": img.get("CLOUDY_PIXEL_PERCENTAGE")
            })

        fc = ee.FeatureCollection(collection.map(extract_values))
        fc_info = fc.getInfo()

        results = []
        for f in fc_info["features"]:
            props = f["properties"]
            if props["NDVI"] is None or props["NDWI"] is None or props["NSMI"] is None:
                continue
            results.append({
                "date": props["date"],
                "NDVI": round(float(props["NDVI"]), 4),
                "NDWI": round(float(props["NDWI"]), 4),
                "NSMI": round(float(props["NSMI"]), 4),
                "cloud_cover": float(props.get("cloud_cover", 0))
            })

        results.sort(key=lambda x: x["date"])

        if not results:
            return jsonify({"success": False, "error": "No valid index values in timeseries"}), 404

        # Basic stats
        def avg(arr, key): return round(sum(x[key] for x in arr) / len(arr), 4)

        stats = {
            "avg_ndvi": avg(results, "NDVI"),
            "avg_ndwi": avg(results, "NDWI"),
            "avg_nsmi": avg(results, "NSMI"),
        }

        return jsonify({
            "success": True,
            "point": {"lat": lat, "lng": lng},
            "data": results,
            "count": len(results),
            "image_count": count,
            "date_range": f"{results[0]['date']} to {results[-1]['date']}",
            "statistics": stats
        })

    except Exception as e:
        logger.error(f"Error in /api/timeseries: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------- Main -------------------- #

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    logger.info(f"Starting Flask app on {host}:{port}, debug={debug_mode}")
    app.run(debug=debug_mode, host=host, port=port)
