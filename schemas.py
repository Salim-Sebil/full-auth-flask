import re

from marshmallow import (
    Schema,
    ValidationError,
    fields,
    pre_load,
    validate,
    validates_schema,
)


class TrimStringsSchema(Schema):
    trim_fields = ()

    @pre_load
    def trim_strings(self, data, **kwargs):
        if isinstance(data, dict):
            return {
                key: value.strip()
                if key in self.trim_fields and isinstance(value, str)
                else value
                for key, value in data.items()
            }
        return data


class AuthSchema(TrimStringsSchema):
    trim_fields = ("username",)

    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=32),
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, max=72),
    )

    @validates_schema
    def validate_username_format(self, data, **kwargs):
        username = data.get("username")
        if username and not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            raise ValidationError(
                {
                    "username": [
                        "Use only letters, numbers, periods, underscores, or hyphens."
                    ]
                }
            )
        password = data.get("password")
        if password and len(password.encode("utf-8")) > 72:
            raise ValidationError(
                {
                    "password": [
                        "Password must be at most 72 bytes when encoded as UTF-8."
                    ]
                }
            )


class NoteSchema(TrimStringsSchema):
    trim_fields = ("title", "category")

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    title = fields.String(required=True, validate=validate.Length(min=1, max=120))
    content = fields.String(load_default="", validate=validate.Length(max=10000))
    category = fields.String(
        load_default="general",
        validate=validate.Length(min=1, max=50),
    )
    is_pinned = fields.Boolean(load_default=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class NotePatchSchema(TrimStringsSchema):
    trim_fields = ("title", "category")

    title = fields.String(validate=validate.Length(min=1, max=120))
    content = fields.String(validate=validate.Length(max=10000))
    category = fields.String(validate=validate.Length(min=1, max=50))
    is_pinned = fields.Boolean()
