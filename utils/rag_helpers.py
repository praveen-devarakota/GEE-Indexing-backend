def clean_none_values(data):
    return [
        {k: (0 if v is None else v) for k, v in item.items()}
        for item in data
    ]