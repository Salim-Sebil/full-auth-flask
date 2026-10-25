from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from werkzeug.exceptions import NotFound

from extensions import db
from models import Note
from schemas import NotePatchSchema, NoteSchema


notes_api = Blueprint("notes", __name__, url_prefix="/notes")
note_schema = NoteSchema()
note_patch_schema = NotePatchSchema()


def current_user_id():
    return int(get_jwt_identity())


def load_json(schema, *, partial=False):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError({"_schema": ["A JSON object is required."]})
    return schema.load(payload, partial=partial)


def get_owned_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user_id()).first()
    if note is None:
        raise NotFound("Note not found.")
    return note


@notes_api.get("")
@jwt_required()
def list_notes():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        raise ValidationError(
            {"pagination": ["page and per_page must be positive integers."]}
        ) from None
    if page < 1 or per_page < 1:
        raise ValidationError(
            {"pagination": ["page and per_page must be positive integers."]}
        )
    per_page = min(per_page, 100)

    pagination = (
        Note.query.filter_by(user_id=current_user_id())
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc(), Note.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return jsonify(
        {
            "notes": [note.to_dict() for note in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@notes_api.post("")
@jwt_required()
def create_note():
    data = load_json(note_schema)
    note = Note(**data, user_id=current_user_id())
    db.session.add(note)
    db.session.commit()
    return jsonify({"note": note.to_dict()}), 201


@notes_api.get("/<int:note_id>")
@jwt_required()
def read_note(note_id):
    return jsonify({"note": get_owned_note(note_id).to_dict()})


@notes_api.patch("/<int:note_id>")
@notes_api.put("/<int:note_id>")
@jwt_required()
def update_note(note_id):
    note = get_owned_note(note_id)
    if request.method == "PUT":
        data = load_json(note_schema)
    else:
        data = load_json(note_patch_schema, partial=True)
    if request.method == "PATCH" and not data:
        raise ValidationError({"_schema": ["At least one field is required."]})
    for key, value in data.items():
        setattr(note, key, value)
    db.session.commit()
    return jsonify({"note": note.to_dict()})


@notes_api.delete("/<int:note_id>")
@jwt_required()
def delete_note(note_id):
    note = get_owned_note(note_id)
    db.session.delete(note)
    db.session.commit()
    return "", 204
