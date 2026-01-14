from flask import Flask
from app.config import Config
from app.firebase_app import init_firebase
from app.utils import init_session_interface

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_firebase(app)
    init_session_interface(app)

    @app.context_processor
    def inject_firebase_config():
        return {"firebase_config": app.config.get("FIREBASE_CONFIG", {})}

    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.social_routes import social_bp
    from app.routes.tutor_routes import tutor_bp
    from app.routes.rides_routes import rides_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.ai_routes import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(rides_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(ai_bp)

    return app
