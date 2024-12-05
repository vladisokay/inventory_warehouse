import json

import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy import text

from back.db import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']
        role_id = data.get('role_id', 3)

        result = db.session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()

        if result:
            return jsonify({"message": "User already exists"}), 400

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        db.session.execute(
            text("INSERT INTO users (username, password_hash, role_id) VALUES (:username, :password_hash, :role_id)"),
            {"username": username, "password_hash": password_hash.decode('utf-8'), "role_id": role_id}
        )
        db.session.commit()

        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        result = db.session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()

        if result:
            user_id = result[0]
            password_hash = result[2]
            role_id = result[3]

            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                identity = json.dumps({'user_id': str(user_id), 'role_id': role_id})
                access_token = create_access_token(identity=identity)
                return jsonify(access_token=access_token), 200
            else:
                return jsonify({"message": "Неверное имя пользователя или пароль"}), 401
        else:
            return jsonify({"message": "Неверное имя пользователя или пароль"}), 401

    except Exception as e:
        return jsonify({"message": f"Серверная ошибка: {str(e)}"}), 500

