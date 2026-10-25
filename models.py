from datetime import datetime, timezone
import re

from sqlalchemy.orm import validates

from extensions import bcrypt, db


def utc_now():
    return datetime.now(timezone.utc)


def normalize_username(value):
    if not isinstance(value, str):
        raise ValueError("Username must be a string.")
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", value):
        raise ValueError(
            "Username must be 3-32 characters and contain only letters, "
            "numbers, periods, underscores, or hyphens."
        )
    return value


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    notes = db.relationship(
        "Note",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("username")
    def validate_username(self, _key, value):
        return normalize_username(value)

    def set_password(self, password):
        if (
            not isinstance(password, str)
            or len(password) < 8
            or len(password.encode("utf-8")) > 72
        ):
            raise ValueError("Password must be 8-72 bytes when encoded as UTF-8.")
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "username": self.username}


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(50), nullable=False, default="general")
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="notes")

    @validates("title")
    def validate_title(self, _key, value):
        if not isinstance(value, str):
            raise ValueError("Title must be a string.")
        value = value.strip()
        if not value or len(value) > 120:
            raise ValueError("Title must contain 1-120 characters.")
        return value

    @validates("category")
    def validate_category(self, _key, value):
        if not isinstance(value, str):
            raise ValueError("Category must be a string.")
        value = value.strip()
        if not value or len(value) > 50:
            raise ValueError("Category must contain 1-50 characters.")
        return value

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "is_pinned": self.is_pinned,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
