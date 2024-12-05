import json
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity


def role_required(required_role_ids):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identity = get_jwt_identity()
            if isinstance(identity, str):
                identity = json.loads(identity)
            if identity and identity['role_id'] in required_role_ids:
                return f(*args, **kwargs)
            else:
                return jsonify({"message": "Доступ запрещен"}), 403
        return decorated_function
    return decorator
