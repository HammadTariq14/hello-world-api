#!/usr/bin/env python3
"""
Simple Hello World API
Exposes /v1/hello endpoint
Note: CORS is handled by APISIX gateway, not in the application
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
from datetime import datetime, timezone

app = Flask(__name__)

# CORS:
# - In AKS behind APISIX: keep CORS OFF here to avoid duplicate headers (APISIX handles it).
# - In local docker-compose: set ENABLE_CORS=true so browser calls from http://localhost:3000 work.
if os.environ.get("ENABLE_CORS", "").lower() in ("1", "true", "yes", "on"):
    CORS(
        app,
        resources={r"/v1/*": {"origins": ["http://localhost:3000"]}},
        supports_credentials=True,
    )

@app.route('/v1/hello', methods=['GET'])
def hello():
    """Return hello message"""
    return jsonify({
        "message": "hi there",
        "status": "success"
    })

@app.route('/v1/time', methods=['GET'])
def time():
    """Return current server time (UTC)"""
    now = datetime.now(timezone.utc)
    return jsonify({
        "utc": now.isoformat(),
        "epoch_seconds": int(now.timestamp())
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
