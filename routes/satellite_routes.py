from flask import Blueprint
from controllers.satellite_controller import (
    health_check,
    api_health,
    composite,
    timeseries,
    analyze_rag,   # 🔥 NEW
    chat_rag       # 🔥 NEW
)

satellite_bp = Blueprint("satellite", __name__)

# Health
satellite_bp.route("/health", methods=["GET"])(health_check)
satellite_bp.route("/api/health", methods=["GET"])(api_health)

# Existing APIs
satellite_bp.route(
    "/api/composite",
    methods=["POST", "OPTIONS"]
)(composite)

satellite_bp.route(
    "/api/timeseries",
    methods=["POST", "OPTIONS"]
)(timeseries)


# -------------------- 🔥 RAG APIs -------------------- #

satellite_bp.route(
    "/api/analyze",
    methods=["POST"]
)(analyze_rag)

satellite_bp.route(
    "/api/chat",
    methods=["POST"]
)(chat_rag)