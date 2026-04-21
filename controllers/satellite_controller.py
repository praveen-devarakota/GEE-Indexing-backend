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

        collection = get_s2_collection(geom, start_date, end_date, max_cloud).sort("system:time_start")

        count = collection.size().getInfo()
        if count == 0:
            return jsonify({"success": False, "error": "No images found"}), 404

        base_image = collection.median().clip(geom)

        if index_type == "NDVI":
            index_image = base_image.select("NDVI")
            vis_params = {"min": -1, "max": 1, "palette": ["#0000ff", "#ffffff", "#00ff00"]}
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

def create_weekly_composites(collection, start_date, end_date):
    start = ee.Date(start_date)
    end = ee.Date(end_date)

    n_days = end.difference(start, "day")
    step = 7  # ~4–5 scenes/month

    def make_composite(i):
        i = ee.Number(i)
        start_i = start.advance(i, "day")
        end_i = start_i.advance(step, "day")

        subset = collection.filterDate(start_i, end_i)

        composite = ee.Image(
            ee.Algorithms.If(
                subset.size().gt(0),
                subset.median(),
                ee.Image.constant(0).rename("NDVI")  # safe fallback
            )
        )

        return composite.set({
            "system:time_start": start_i.millis()
        })

    indices = ee.List.sequence(0, n_days.subtract(1), step)
    return ee.ImageCollection(indices.map(make_composite))


def timeseries():

    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.get_json() or {}

        point = data.get("point", {})
        lat = point.get("lat")
        lng = point.get("lng")

        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if lat is None or lng is None:
            return jsonify({"success": False, "error": "Missing latitude or longitude"}), 400

        geom = ee.Geometry.Point([float(lng), float(lat)])

        # Step 1: Raw collection
        raw_collection = get_s2_collection(geom, start_date, end_date, 60)

        # Step 2: Weekly composites
        collection = create_weekly_composites(
            raw_collection, start_date, end_date
        ).sort("system:time_start")

        # Step 3: Extract NDVI safely
        def extract(img):
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom.buffer(50),
                scale=10,
                maxPixels=1e9
            )

            ndvi = ee.Algorithms.If(
                stats.contains("NDVI"),
                stats.get("NDVI"),
                None
            )

            return ee.Feature(None, {
                "date": img.date().format("YYYY-MM-dd"),
                "NDVI": ndvi
            })

        fc = ee.FeatureCollection(collection.map(extract)).getInfo()

        # Step 4: Clean data
        series = []

        for f in fc.get("features", []):
            props = f.get("properties", {})
            ndvi = props.get("NDVI")

            if ndvi is None:
                continue

            try:
                ndvi = float(ndvi)
            except:
                continue

            if ndvi < -0.2 or ndvi > 1:
                continue

            series.append({
                "date": props.get("date"),
                "NDVI": round(ndvi, 4)
            })

        series.sort(key=lambda x: x["date"])

        # Step 5: Smooth NDVI
        def smooth(values):
            smoothed = []
            for i in range(len(values)):
                neighbors = values[max(0, i-1):min(len(values), i+2)]
                smoothed.append(sum(neighbors) / len(neighbors))
            return smoothed

        if series:
            ndvi_vals = [r["NDVI"] for r in series]
            smooth_vals = smooth(ndvi_vals)

            for i, r in enumerate(series):
                r["NDVI"] = round(smooth_vals[i], 4)

        return jsonify({
            "success": True,
            "data": series,
            "count": len(series)
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