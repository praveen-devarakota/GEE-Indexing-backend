import traceback
from flask import jsonify, request
import ee
import datetime
from services.rag_service import analyze_with_rag, chat_with_rag
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
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json() or {}

        geometry = data.get("geometry")
        start_date = data.get("start_date", "2017-06-23")
        end_date = data.get("end_date", datetime.datetime.now().strftime("%Y-%m-%d"))
        max_cloud = float(data.get("max_cloud", 80))
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

        return jsonify({
            "success": True,
            "index_type": index_type,
            "image_count": count,
            "tile_url": map_id["tile_fetcher"].url_format,
            "vis_params": vis_params,
            "date_range": f"{start_date} to {end_date}",
            "scale": scale
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------- TIME SERIES -------------------- #

def compute_derivatives(values):
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
        print("🔥 NEW CODE RUNNING")

        data = request.get_json() or {}

        point = data.get("point", {})
        lat = point.get("lat")
        lng = point.get("lng")

        ranges = data.get("ranges", [])

        single_mode = False
        if not ranges and data.get("start_date") and data.get("end_date"):
            ranges = [{
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date")
            }]
            single_mode = True
        elif ranges and len(ranges) == 1:
            single_mode = True

        if lat is None or lng is None:
            return jsonify({"success": False, "error": "Missing latitude or longitude"}), 400

        geom = ee.Geometry.Point([float(lng), float(lat)])

        all_results = []

        for range_obj in ranges:

            start_date = range_obj.get("start_date")
            end_date = range_obj.get("end_date")

            if not validate_date_range(start_date, end_date):
                continue

            # 🔥 NO CLOUD FILTER + SORT BY TIME
            collection = get_s2_collection(
                geom, start_date, end_date, 100
            ).sort("system:time_start")

            def extract(img):
                stats = img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom.buffer(50),
                    scale=10,
                    maxPixels=1e9
                )

                return ee.Feature(None, {
                    "date": img.date().format("YYYY-MM-dd"),
                    "NDVI": stats.get("NDVI"),
                    "NDWI": stats.get("NDWI"),
                    "NSMI": stats.get("NSMI")
                })

            # 🔥 INCREASE LIMIT
            fc = ee.FeatureCollection(collection.map(extract)).limit(2000).getInfo()

            series = []

            for f in fc.get("features", []):
                props = f.get("properties", {})

                # 🔥 KEEP ALL SCENES
                series.append({
                    "date": props.get("date"),
                    "NDVI": None if props.get("NDVI") is None else round(float(props["NDVI"]), 4),
                    "NDWI": None if props.get("NDWI") is None else round(float(props["NDWI"]), 4),
                    "NSMI": None if props.get("NSMI") is None else round(float(props["NSMI"]), 4)
                })

            series.sort(key=lambda x: x["date"])

            # DERIVATIVES
            if single_mode and series:

                ndvi_vals = [r["NDVI"] or 0 for r in series]
                ndwi_vals = [r["NDWI"] or 0 for r in series]
                nsmi_vals = [r["NSMI"] or 0 for r in series]

                ndvi_d1, ndvi_d2 = compute_derivatives(ndvi_vals)
                ndwi_d1, ndwi_d2 = compute_derivatives(ndwi_vals)
                nsmi_d1, nsmi_d2 = compute_derivatives(nsmi_vals)

                for i, r in enumerate(series):
                    r["NDVI_d1"] = None if ndvi_d1[i] is None else round(ndvi_d1[i], 5)
                    r["NDVI_d2"] = None if ndvi_d2[i] is None else round(ndvi_d2[i], 5)

                    r["NDWI_d1"] = None if ndwi_d1[i] is None else round(ndwi_d1[i], 5)
                    r["NDWI_d2"] = None if ndwi_d2[i] is None else round(ndwi_d2[i], 5)

                    r["NSMI_d1"] = None if nsmi_d1[i] is None else round(nsmi_d1[i], 5)
                    r["NSMI_d2"] = None if nsmi_d2[i] is None else round(nsmi_d2[i], 5)

            all_results.append({
                "range": f"{start_date} to {end_date}",
                "data": series
            })

        return jsonify({
            "success": True,
            "data": all_results[0]["data"],
            "count": len(all_results[0]["data"])
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
# -------------------- RAG ANALYSIS -------------------- #
def analyze_rag():
    try:
        data = request.get_json() or {}

        series = data.get("data")

        if not series:
            return jsonify({
                "success": False,
                "error": "Missing 'data'"
            }), 400

        # 🔥 Call RAG service
        result = analyze_with_rag(series)

        return jsonify({
            "success": True,
            "analysis": result
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# -------------------- RAG CHAT -------------------- #

def chat_rag():
    try:
        data = request.get_json() or {}

        question = data.get("question")

        if not question:
            return jsonify({
                "success": False,
                "error": "Missing 'question'"
            }), 400

        # 🔥 Call RAG chat
        answer = chat_with_rag(question)

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500