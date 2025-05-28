from flask import g, request
from functools import wraps
from firebase_admin import auth

def require_firebase_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not id_token:
            return {"error": "Unauthorized"}, 401
        try:
            decoded_token = auth.verify_id_token(id_token)
            g.user = {
                "uid": decoded_token["uid"],
                "is_anonymous": decoded_token.get("firebase", {}).get("sign_in_provider") == "anonymous"
            }
        except Exception:
            return {"error": "Invalid or expired token"}, 401
        return f(*args, **kwargs)
    return decorated_function
