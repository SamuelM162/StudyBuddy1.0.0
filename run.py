import os
from dotenv import load_dotenv
load_dotenv(".env")
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", str(app.config.get("PORT", 5001))))
    debug = bool(app.config.get("DEBUG", False)) and app.config.get("ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
