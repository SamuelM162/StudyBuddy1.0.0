from flask import Flask, current_app
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Firebase config available in all templates ---
    @app.context_processor
    def inject_firebase_config():
        return {
            "firebase_config": {
                "apiKey": app.config.get("FIREBASE_API_KEY"),
                "authDomain": app.config.get("FIREBASE_AUTH_DOMAIN"),
                "databaseURL": app.config.get("FIREBASE_DATABASE_URL"),
                "projectId": app.config.get("FIREBASE_PROJECT_ID"),
                "appId": app.config.get("FIREBASE_APP_ID"),
            }
        }

    # import and register blueprints here if they exist
    from app.routes.auth_routes import auth_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.social_routes import social_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.ai_routes import ai_bp
    from app.routes.rides_routes import rides_bp
    from app.routes.tutor_routes import tutor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(rides_bp)
    app.register_blueprint(tutor_bp)

    return app
