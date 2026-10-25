from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User, normalize_username
from schemas import AuthSchema


auth = Blueprint("auth", __name__, url_prefix="/auth")
auth_schema = AuthSchema()


def load_auth_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError({"_schema": ["A JSON object is required."]})
    return auth_schema.load(payload)


def token_response(user, status=200):
    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), status


@auth.post("/signup")
def signup():
    data = load_auth_payload()
    username = normalize_username(data["username"])
    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"error": "Username is already taken."}), 409

    user = User(username=username)
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username is already taken."}), 409
    return token_response(user, 201)


@auth.post("/login")
def login():
    data = load_auth_payload()
    try:
        username = normalize_username(data["username"])
    except ValueError:
        username = ""
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid username or password."}), 401
    return token_response(user)


@auth.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()})
