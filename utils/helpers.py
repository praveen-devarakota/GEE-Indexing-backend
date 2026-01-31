import datetime

def validate_date_range(start_date, end_date):
    try:
        s = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        e = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        return s < e
    except ValueError:
        return False
