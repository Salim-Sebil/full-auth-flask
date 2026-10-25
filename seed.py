from extensions import db
from models import Note, User


def seed_data():
    user = User.query.filter_by(username="demo").first()
    if user is None:
        user = User(username="demo")
        user.set_password("demo-password")
        db.session.add(user)
        db.session.flush()

    if not user.notes:
        user.notes.extend(
            [
                Note(
                    title="Welcome",
                    content="This is your first note. Edit or delete it as you like.",
                    category="personal",
                    is_pinned=True,
                ),
                Note(
                    title="Plan the week",
                    content="Add your priorities and next steps here.",
                    category="planning",
                ),
            ]
        )
    db.session.commit()
