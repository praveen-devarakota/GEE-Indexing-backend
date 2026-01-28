from flask import Flask, jsonify, request
from flask_cors import CORS
import ee
import datetime
import os
import json
import logging

# -------------------- Logging -------------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Flask App -------------------- #
app = Flask(__name__)
CORS(app)

# -------------------- Earth Engine Init -------------------- #
def init_earth_engine():
    try:
        sa_json = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")

        # Production (Render)
        if sa_json:
            service_account_info = json.loads(sa_json)

            credentials = ee.ServiceAccountCredentials(
                service_account_info["client_email"],
                key_data=service_account_info
            )

            ee.Initialize(
                credentials,
                project=service_account_info["project_id"]
            )

            logger.info("Earth Engine initialized using service account (Render).")

        # Local development
        else:
            ee.Initialize(project="flask-backend-478306")
            logger.info("Earth Engine initialized using local user credentials.")

    except Exception as e:
        logger.error(f"Error initializing Earth Engine: {e}")
        raise RuntimeError(f"Error initializing Earth Engine: {e}")


# Initialize once at startup
init_earth_engine()

# -------------------- Utility Functions -------------------- #
def validate_date_range(start_date, end_date):
    try:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        return start_dt < end_dt
    except ValueError:
        return False


def mask_s2_clouds(image):
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
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
    nsmi = image.normalizedDifference(["B8", "B11"]).rename("NSMI")
    return image.addBands([ndvi, ndwi, nsmi])


def get_s2_collection(geom, start_date, end_date, max_cloud):
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
        .map(mask_s2_clouds)
        .map(add_indices)
    )

# -------------------- Routes -------------------- #

@app.route("/health", methods=["GET"])
def root_health():
    return jsonify({"status": "ok"})


@app.route("/api/health", methods=["GET"])
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
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/composite", methods=["POST"])
def composite():
    try:
        data = request.get_json()
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

        collection = get_s2_collection(
            geom, start_date, end_date, max_cloud
        )
        count = collection.size().getInfo()

        if count == 0:
            return jsonify(
                {"success": False, "error": "No images found"}
            ), 404

        base_image = collection.median().clip(geom)

        if index_type == "NDVI":
            index_image = base_image.select("NDVI")
            vis_params = {
                "min": -1, "max": 1,
                "palette": ["#0000ff", "#ffffff", "#00ff00"]
            }
        elif index_type == "NDWI":
            index_image = base_image.select("NDWI")
            vis_params = {
                "min": -1, "max": 1,
                "palette": ["#8b4513", "#ffffff", "#0000ff"]
            }
        elif index_type == "NSMI":
            index_image = base_image.select("NSMI")
            vis_params = {
                "min": -1, "max": 1,
                "palette": ["#ffff00", "#ffffff", "#ff0000"]
            }
        elif index_type == "TRUE_COLOR":
            index_image = base_image.select(["B4", "B3", "B2"])
            vis_params = {"min": 0, "max": 3000}
        else:
            return jsonify({"success": False, "error": "Invalid index_type"}), 400

        map_id = ee.Image(index_image).getMapId(vis_params)
        tile_url = map_id["tile_fetcher"].url_format

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
            "tile_url": tile_url,
            "download_url": download_url,
            "vis_params": vis_params,
            "date_range": f"{start_date} to {end_date}",
            "scale": scale
        })

    except Exception as e:
        logger.error(f"Composite error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/timeseries", methods=["POST"])
def timeseries():
    try:
        data = request.get_json()
        point = data.get("point", {})
        lat = float(point.get("lat"))
        lng = float(point.get("lng"))

        start_date = data.get("start_date", "2017-06-23")
        end_date = data.get(
            "end_date",
            datetime.datetime.now().strftime("%Y-%m-%d")
        )
        max_cloud = float(data.get("max_cloud", 30))

        if not validate_date_range(start_date, end_date):
            return jsonify({"success": False, "error": "Invalid date range"}), 400

        geom = ee.Geometry.Point([lng, lat])
        collection = get_s2_collection(
            geom, start_date, end_date, max_cloud
        )

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
                "NSMI": stats.get("NSMI"),
                "cloud": img.get("CLOUDY_PIXEL_PERCENTAGE")
            })

        fc = ee.FeatureCollection(collection.map(extract)).getInfo()

        results = [
            {
                "date": f["properties"]["date"],
                "NDVI": round(float(f["properties"]["NDVI"]), 4),
                "NDWI": round(float(f["properties"]["NDWI"]), 4),
                "NSMI": round(float(f["properties"]["NSMI"]), 4),
                "cloud_cover": float(f["properties"]["cloud"])
            }
            for f in fc["features"]
            if f["properties"]["NDVI"] is not None
        ]

        results.sort(key=lambda x: x["date"])

        return jsonify({
            "success": True,
            "data": results,
            "count": len(results)
        })

    except Exception as e:
        logger.error(f"Timeseries error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------- Main -------------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
