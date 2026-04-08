import ee

def mask_s2_clouds(image):
    scl = image.select("SCL")
    good = (
        scl.eq(2)   # dark features
        .Or(scl.eq(4))  # vegetation
        .Or(scl.eq(5))  # bare soil
        .Or(scl.eq(6))  # water
        .Or(scl.eq(11)) # snow/ice
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
        # 🔥 REMOVED CLOUD FILTER (IMPORTANT)
        .map(mask_s2_clouds)
        .map(add_indices)
    )