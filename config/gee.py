import ee
import os
import tempfile
import logging
import threading

logger = logging.getLogger(__name__)

_gee_initialized = False
_gee_lock = threading.Lock()


def init_earth_engine():
    """
    Initializes Google Earth Engine exactly once.
    Safe to call multiple times.
    """
    global _gee_initialized

    if _gee_initialized:
        return

    with _gee_lock:
        if _gee_initialized:
            return

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

            _gee_initialized = True

        except Exception as e:
            logger.error("Error initializing Earth Engine", exc_info=True)
            raise RuntimeError("Earth Engine initialization failed") from e