# Full Auth Lab: Flask Notes API

A JWT-authenticated Flask API for registering users and managing personal,
user-owned notes. Passwords are stored as bcrypt hashes. Every note operation
is scoped to the authenticated user, and the notes index supports pagination.

## Requirements

- Python 3.10 or newer
- pip

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set a stable secret before running outside local development.
export JWT_SECRET_KEY="replace-with-a-long-random-secret"
flask --app app init-db
flask --app app seed
flask --app app run --debug
```

On Windows PowerShell, activate the virtual environment with
`.venv\Scripts\Activate.ps1`. The development server is available at
`http://127.0.0.1:5000`. The default SQLite database is `instance/notes.db`;
set `DATABASE_URL` to use another SQLAlchemy database URL. If `JWT_SECRET_KEY`
is omitted, the app generates a random key at startup, so tokens will be
invalidated when the process restarts. Set a stable, long random secret outside
local development. Set `CORS_ORIGINS` to a comma-separated
list of trusted frontend origins if they differ from localhost ports 3000 and
5173.

The seed command is safe to re-run. It creates the demo account
`demo` / `demo-password` and two starter notes if they do not already exist.
Change the demo password before using seeded data outside local development.

## Authentication API

Send and receive JSON. Signup and login return an access token and public user
object. Include the token on protected requests as
`Authorization: Bearer <access_token>`. Tokens expire after one hour; for JWT
logout, the client should discard its token.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/signup` | Create an account (`username`, `password`), return `201` |
| POST | `/auth/login` | Authenticate and return a JWT |
| GET | `/auth/me` | Return the current user; requires a valid JWT |

Usernames are trimmed, normalized to lowercase, and unique. They must contain
3-32 letters, numbers, periods, underscores, or hyphens. Passwords must be at
least 8 characters. Password hashes are never returned by the API.

## Notes API

Every `/notes` endpoint requires a valid bearer token. A note has a required
`title` and supports `content`, `category`, and `is_pinned` fields. The
authenticated user ID is assigned by the server and cannot be supplied or
changed by clients.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/notes?page=1&per_page=10` | List the current user's notes with pagination metadata |
| POST | `/notes` | Create a note (`title`, optional `content`, `category`, `is_pinned`) |
| GET | `/notes/<note_id>` | Read one of the current user's notes |
| PATCH | `/notes/<note_id>` | Update one or more note fields |
| PUT | `/notes/<note_id>` | Replace a note; title is required and omitted optional fields reset to defaults |
| DELETE | `/notes/<note_id>` | Delete a note; returns `204` |

Pagination defaults to page 1 with 10 results per page, and `per_page` is
capped at 100. The index response contains `notes` and a `pagination` object
with `page`, `per_page`, `total`, `pages`, `has_next`, and `has_prev`. A note
owned by another user is reported as `404`, preventing resource enumeration.
Invalid input returns `400`, unauthenticated requests return `401`, and
duplicate usernames return `409`.

## Tests

Run the API tests with:

```bash
pytest
```
