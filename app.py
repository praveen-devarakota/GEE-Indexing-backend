from dotenv import load_dotenv
load_dotenv()
from config.database import init_database
from routes.auth_routes import auth_bp
from flask import Flask, app, jsonify
from flask_cors import CORS
from config.gee import init_earth_engine
from routes.satellite_routes import satellite_bp
import os


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(satellite_bp)
    app.register_blueprint(auth_bp)
    
    init_database()
    init_earth_engine()

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "status": "success",
            "message": "Satellite API is running 🚀",
            "available_routes": [
                "/api/satellite/...",
                "/api/analyze"
            ]
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)