import ee

def mask_s2_clouds(image):
    scl = image.select("SCL")
    
    # Keep only vegetation & soil
    good_scl = (
        scl.eq(4)   # vegetation
        .Or(scl.eq(5))  # bare soil
    )
    
    # QA60 cloud + cirrus mask
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    
    qa_mask = qa.bitwiseAnd(cloud_bit).eq(0).And(
        qa.bitwiseAnd(cirrus_bit).eq(0)
    )
    
    mask = good_scl.And(qa_mask)
    
    return image.updateMask(mask).copyProperties(image, image.propertyNames())


def add_indices(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands([ndvi])


def get_s2_collection(geom, start_date, end_date, max_cloud):
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))  # balanced filter
        .map(mask_s2_clouds)
        .map(add_indices)
    )