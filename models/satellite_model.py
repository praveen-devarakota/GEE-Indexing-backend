import ee

def mask_s2_clouds(image):
    scl = image.select("SCL")
    good = (
        scl.eq(2)
        .Or(scl.eq(4))
        .Or(scl.eq(5))
        .Or(scl.eq(6))
        .Or(scl.eq(11))
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
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
        .map(mask_s2_clouds)
        .map(add_indices)
    )
