import os
import secrets

import click
from flask import Flask, jsonify
from flask_cors import CORS
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from auth_routes import auth
from extensions import bcrypt, db, jwt
from note_routes import notes_api


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///notes.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(32),
        JWT_ACCESS_TOKEN_EXPIRES=3600,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    CORS(
        app,
        resources={
            r"/auth/*": {"origins": allowed_origins},
            r"/notes*": {"origins": allowed_origins},
        },
    )
    app.register_blueprint(auth)
    app.register_blueprint(notes_api)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({"errors": error.messages}), 400

    @app.cli.command("init-db")
    def init_db():
        """Create the application's database tables."""
        with app.app_context():
            db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    def seed_database():
        """Create a demo user and starter notes."""
        from seed import seed_data

        with app.app_context():
            seed_data()
        click.echo("Demo user and notes are ready.")

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
