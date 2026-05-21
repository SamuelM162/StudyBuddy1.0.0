from flask import Flask, jsonify, request
from app.config import Config
from app.firebase_app import init_firebase
from app.i18n import get_language, tr
from app.universities import UNIVERSITIES
from app.utils import get_csrf_token, init_session_interface, should_enforce_csrf, validate_csrf

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["DEFAULT_LANGUAGE"] = "en"
    app.config["LANGUAGES"] = ["en", "sk"]

    if app.config.get("IS_PRODUCTION") and app.config.get("SECRET_KEY") == "dev-secret-key-change-me":
        raise RuntimeError("SECRET_KEY must be configured for production")

    init_firebase(app)
    init_session_interface(app)

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "service": "studypeer"})

    @app.before_request
    def csrf_protect():
        if should_enforce_csrf():
            validate_csrf()

    @app.context_processor
    def inject_firebase_config():
        full_path = request.full_path if request.full_path else request.path
        return {
            "current_language": get_language(),
            "csrf_input": lambda: f'<input type="hidden" name="_csrf_token" value="{get_csrf_token()}">',
            "csrf_token": get_csrf_token,
            "firebase_config": app.config.get("FIREBASE_CONFIG", {}),
            "request_path_with_query": full_path.rstrip("?"),
            "tr": tr,
            "universities": UNIVERSITIES,
        }

    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.social_routes import social_bp
    from app.routes.forum_routes import forum_bp
    from app.routes.tutor_routes import tutor_bp
    from app.routes.rides_routes import rides_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.ai_routes import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(rides_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(ai_bp)

    return app
