import os
from flask import Flask
from flask_cors import CORS
from routes import api, main
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(main)
app.register_blueprint(api, url_prefix='/api')

if __name__ == '__main__':
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = bool(int(os.getenv("FLASK_DEBUG", 1)))

    app.run(host=host, port=port, debug=debug)
