import ee
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

def init_earth_engine():
    try:
        sa_json = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")

        # -------- Production (Render) --------
        if sa_json:
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as f:
                f.write(sa_json)
                key_path = f.name

            credentials = ee.ServiceAccountCredentials(
                email=None,
                key_file=key_path
            )

            ee.Initialize(credentials)
            logger.info("Earth Engine initialized using service account.")

        # -------- Local --------
        else:
            ee.Initialize(project="flask-backend-478306")
            logger.info("Earth Engine initialized using local credentials.")

    except Exception as e:
        logger.error(f"Error initializing Earth Engine: {e}")
        raise RuntimeError(e)
