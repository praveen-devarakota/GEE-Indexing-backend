import json
from rag.chunking import chunk_time_series
from rag.summarizer import summarize_chunks
from rag.prompt_builder import build_analysis_prompt, build_chat_prompt
from rag.memory import set_memory, get_memory
from rag.llm_handler import generate_response


# 🔥 Intelligence layer
def enrich_summary(summary, data):
    insights = []

    ndvi_vals = [d["NDVI"] for d in data if d["NDVI"] is not None]
    ndwi_vals = [d["NDWI"] for d in data if d["NDWI"] is not None]

    # ---- TREND ----
    if len(ndvi_vals) >= 2:
        if ndvi_vals[-1] > ndvi_vals[0]:
            insights.append("Overall vegetation increased over time")
        else:
            insights.append("Overall vegetation decreased over time")

    # ---- SHARP DROPS ----
    for i in range(1, len(data)):
        prev = data[i - 1]["NDVI"]
        curr = data[i]["NDVI"]

        if prev is not None and curr is not None and (prev - curr) > 0.05:
            insights.append(f"Sharp vegetation drop around {data[i]['date']}")

    # ---- WATER TREND ----
    if len(ndwi_vals) >= 2:
        if ndwi_vals[-1] > ndwi_vals[0]:
            insights.append("Water content increased")
        else:
            insights.append("Water content decreased")

    # ---- MISSING DATA ----
    missing = sum(1 for d in data if d["NDVI"] is None)
    if missing > 0:
        insights.append(f"{missing} missing NDVI observations detected")

    return summary + "\n\nComputed Insights:\n" + "\n".join(insights)


def run_analysis_pipeline(data):
    chunks = chunk_time_series(data)
    summary = summarize_chunks(chunks)

    summary = enrich_summary(summary, data)

    prompt = build_analysis_prompt(summary)
    raw_response = generate_response(prompt)

    cleaned = raw_response.strip().replace("```json", "").replace("```", "")

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        print("❌ JSON parse error:", e)
        parsed = {
            "trend": "unknown",
            "key_events": [],
            "summary": cleaned
        }

    # ✅ store BOTH analysis + raw data
    set_memory({
        "analysis": parsed,
        "data": data
    })

    return parsed


def run_chat_pipeline(question):
    context = get_memory()

    if not context:
        return {"answer": "No analysis available. Run analysis first."}

    analysis = context.get("analysis", {})
    data = context.get("data", [])

    # 🔥 SORTED DATES
    dates = sorted([d["date"] for d in data if d.get("date")])
    start_date = dates[0] if dates else "unknown"
    end_date = dates[-1] if dates else "unknown"

    # 🔥 GRAPH CURVE (VERY IMPORTANT)
    ndvi_series = [(d["date"], d["NDVI"]) for d in data if d.get("NDVI") is not None]

    # limit size (avoid token overload)
    curve_text = ", ".join([
        f"{date}:{round(val, 2)}" for date, val in ndvi_series[:25]
    ])

    enhanced_context = {
        "analysis": analysis,
        "start_date": start_date,
        "end_date": end_date,
        "curve": curve_text
    }

    prompt = build_chat_prompt(enhanced_context, question)

    raw_response = generate_response(prompt)

    cleaned = raw_response.strip().replace("```json", "").replace("```", "")

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        print("❌ Chat JSON parse error:", e)
        parsed = {"answer": cleaned}

    # 🔥 FIX: flatten response properly
    if isinstance(parsed, dict) and "answer" in parsed:
        return {"answer": parsed["answer"]}

    return {"answer": str(parsed)}