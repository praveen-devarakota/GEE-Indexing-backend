def chunk_time_series(data, chunk_size=10):
    """
    Splits time-series into smaller chunks
    """
    chunks = []

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        chunks.append(chunk)

    return chunks