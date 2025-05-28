import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from flask import request, jsonify

# Initialize only once
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

def verify_token(id_token):
    return auth.verify_id_token(id_token)

def require_firebase_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401

        id_token = auth_header.split("Bearer ")[1]

        try:
            decoded_token = verify_token(id_token)
            request.user = decoded_token  # Optional: user data
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated_function
