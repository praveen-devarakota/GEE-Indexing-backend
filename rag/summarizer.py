def summarize_chunks(chunks):
    summaries = []

    for chunk in chunks:
        ndvi_vals = [d.get("NDVI") or 0 for d in chunk]

        if not ndvi_vals:
            continue

        start = ndvi_vals[0]
        end = ndvi_vals[-1]

        trend = "increasing" if end > start else "decreasing"

        max_val = max(ndvi_vals)
        min_val = min(ndvi_vals)

        summaries.append(
            f"NDVI is {trend} (start: {start}, end: {end}), "
            f"max: {max_val}, min: {min_val}"
        )

    return "\n".join(summaries)