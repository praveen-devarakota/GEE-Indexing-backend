from flask import Flask
from flask_cors import CORS
from config.gee import init_earth_engine
from routes.satellite_routes import satellite_bp

def create_app():
    app = Flask(__name__)
    CORS(app)  # global CORS

    init_earth_engine()
    app.register_blueprint(satellite_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
