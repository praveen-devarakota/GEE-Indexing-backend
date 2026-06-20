def chunk_time_series(data, chunk_size=12):

    chunks = []

    for i in range(0, len(data), chunk_size):

        window = data[i:i + chunk_size]

        if len(window) < 2:
            continue

        values = []
        dates = []

        for row in window:

            try:
                values.append(float(row["NDVI"]))
                dates.append(row["date"])
            except:
                continue

        if len(values) < 2:
            continue

        start_date = dates[0]
        end_date = dates[-1]

        start_ndvi = values[0]
        end_ndvi = values[-1]

        peak = max(values)
        minimum = min(values)

        peak_idx = values.index(peak)
        min_idx = values.index(minimum)

        peak_date = dates[peak_idx]
        min_date = dates[min_idx]

        avg = sum(values) / len(values)

        change = end_ndvi - start_ndvi

        if change > 0.05:
            trend = "increasing"
        elif change < -0.05:
            trend = "decreasing"
        else:
            trend = "stable"

        rises = []
        drops = []

        for j in range(1, len(values)):
            delta = values[j] - values[j - 1]

            if delta > 0:
                rises.append(delta)
            else:
                drops.append(delta)

        largest_rise = max(rises) if rises else 0
        largest_drop = min(drops) if drops else 0

        chunk = f"""
                Period: {start_date} to {end_date}

                Trend: {trend}

                Start NDVI: {start_ndvi:.3f}
                End NDVI: {end_ndvi:.3f}

                Average NDVI: {avg:.3f}

                Peak NDVI: {peak:.3f}
                Peak Date: {peak_date}

                Minimum NDVI: {minimum:.3f}
                Minimum Date: {min_date}

                Largest Rise: {largest_rise:.3f}

                Largest Drop: {largest_drop:.3f}
                """

        chunks.append(chunk)
        print("\n========== CHUNKS GENERATED ==========")

        for idx, chunk in enumerate(chunks):
            print(f"\nChunk {idx+1}")
            print(chunk)

        print("Total Chunks:", len(chunks))
        print("========== END CHUNKS ==========\n")

    return chunks