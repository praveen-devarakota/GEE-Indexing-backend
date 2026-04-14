from flask import Flask, jsonify
from flask_cors import CORS
from config.gee import init_earth_engine
from routes.satellite_routes import satellite_bp
import os

def create_app():
    app = Flask(__name__)
    CORS(app)

    print("API KEY:", os.getenv("GROQ_API_KEY"))

    init_earth_engine()

    app.register_blueprint(satellite_bp)

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