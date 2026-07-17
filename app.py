import os

from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.api import api_bp
from src.config import get_app_settings


def create_app() -> Flask:
    settings = get_app_settings()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length
    app.config["UPLOAD_DIR"] = settings.upload_dir
    os.makedirs(settings.upload_dir, exist_ok=True)

    Limiter(
        get_remote_address,
        app=app,
        storage_uri=settings.redis_url,
        default_limits=[settings.rate_limit],
    )

    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(413)
    def too_large(_e):
        return {"error": "Uploaded file is too large"}, 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
