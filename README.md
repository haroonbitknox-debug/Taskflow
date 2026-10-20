# TaskFlow

TaskFlow is a local full-stack task-management application with a React/Vite
frontend, FastAPI backend, and MySQL database. It includes cookie-based
authentication, role-based access control, task and user management, private
spreadsheet upload/index/search, dashboards, and a chatbot that requires
explicit confirmation before it changes tasks.

## Prerequisites

- Windows 10/11 and VS Code with PowerShell
- Python 3.10 or newer and `py` (the tested environment uses Python 3.12)
- Node.js 20.19 or newer and npm
- A local MySQL or MariaDB server on port 3306
- phpMyAdmin, if desired, for local database administration

This project uses MySQL through PyMySQL. It does not require Docker, SQLite, or
a remote database. phpMyAdmin is a separate local administration tool and is
not required to run the application.

## Local setup and startup

### 1. Start MySQL and create the database

Start MySQL from the local XAMPP/WAMP control panel, or start the installed
Windows service from an elevated PowerShell terminal. To discover its service
name:

```powershell
Get-Service | Where-Object {
    $_.Name -match "mysql|maria" -or $_.DisplayName -match "mysql|maria"
}
```

If the service is present but stopped, start it using its actual service name,
for example `Start-Service MySQL80`. Verify that port 3306 is listening:

```powershell
Test-NetConnection 127.0.0.1 -Port 3306
```

Open the phpMyAdmin URL configured by your local installation. On the
environment used for this verification, <http://127.0.0.1/phpmyadmin/> returns
HTTP 200; XAMPP/WAMP installations may use another local URL. In phpMyAdmin,
create a database named `taskflow_db` with `utf8mb4_unicode_ci` collation.
Migrations create the tables; do not create them manually.

### 2. Configure and start FastAPI

In a VS Code PowerShell terminal, from the project root:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
} else {
    Write-Host "Keeping existing backend/.env; review it instead of overwriting it."
}
```

Edit `backend/.env` and set the actual local MySQL credentials. In particular,
change `DB_PASSWORD` if the MySQL account has a password. Keep this file
private. The checked-in `.env.example` defaults to the local database
`taskflow_db`, root user, and no password; those are examples, not universal
MySQL credentials. The development configuration has a development-only
fallback JWT key. For a local custom key, generate one with
`python -c "import secrets; print(secrets.token_urlsafe(48))"` and set
`JWT_SECRET_KEY` in `backend/.env`. Never use the development fallback in
production.

Apply the schema and (optionally) add development-only sample data:

```powershell
alembic upgrade head
alembic current
python -m db.seeders.seed_demo
```

The seeder is idempotent and is blocked unless `APP_ENV=development` is
explicitly configured. To run FastAPI in this terminal:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks virtual-environment activation, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal,
then activate again. Keep this backend terminal running.

### 3. Configure and start React

Open a second VS Code PowerShell terminal at the project root:

```powershell
cd frontend
npm install
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
} else {
    Write-Host "Keeping existing frontend/.env; review it instead of overwriting it."
}
npm run dev
```

Open <http://localhost:5173>. The frontend's default
`VITE_API_BASE_URL=http://localhost:8000/api` matches the backend. The backend
default CORS origin is `http://localhost:5173`; if either address changes,
update `frontend/.env` and `backend/.env` (`CORS_ORIGINS`) to match. Restart the
respective development server after environment changes.

Service URLs:

- Frontend: <http://localhost:5173>
- Backend root health response: <http://localhost:8000/>
- API health: <http://localhost:8000/api/health>
- Swagger UI: <http://localhost:8000/docs>
- phpMyAdmin: the URL configured by the local installation

The home page's API health card calls the real backend health endpoint.

## Demo data and credentials

After migrations, run `python -m db.seeders.seed_demo` from `backend/` to add
development-only sample data. The seeder requires `APP_ENV=development`,
hashes passwords with Argon2, and is idempotent: rerunning it does not create
duplicate demo users, tasks, tags, or index entries. It creates six accounts,
36 sample tasks, and indexes the tracked sample CSV.

| Role | Email | Password |
| --- | --- | --- |
| Administrator | `admin@taskflow.local` | `TaskFlow-Admin-Dev-2026!` |
| Regular user | `alex@taskflow.local` | `TaskFlow-User-Dev-2026!` |
| Other regular users | `jordan@taskflow.local`, `sam@taskflow.local`, `taylor@taskflow.local`, `casey@taskflow.local` | `TaskFlow-User-Dev-2026!` |

These public credentials are local development fixtures only. Do not use them
on an exposed or production installation. Do not run the seeder against
`taskflow_test_db`; the automated test suite expects a clean test database.

## Project structure and dependencies

```text
TaskFlow/
├── README.md
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── api/routes/       # Auth, users, tasks, files, dashboards, chat
│   │   ├── core/             # Environment-based settings
│   │   ├── db/               # SQLAlchemy session and base
│   │   ├── middleware/
│   │   ├── models/           # Users, tasks, files, chat, audit
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── db/
│   │   ├── migrations/       # Alembic migrations and versions
│   │   ├── seeders/          # Idempotent development fixture seeder
│   │   └── schema.sql        # Reference only; use Alembic to apply
│   ├── tests/
│   └── uploads/
│       ├── demo-fixtures/    # Tracked, non-private sample CSV
│       └── user-files/       # Local private uploads; ignored by Git
└── frontend/
    ├── .env.example
    ├── package.json
    └── src/
        ├── assets/
        ├── components/
        ├── context/
        ├── hooks/
        ├── pages/
        ├── services/
        └── utils/
```

Backend dependencies are declared in `backend/requirements.txt`: FastAPI,
Uvicorn, SQLAlchemy, Pydantic Settings, Alembic, PyMySQL, Argon2, PyJWT,
pandas, openpyxl, xlrd, python-multipart, and pytest/httpx for tests.
Frontend dependencies are in `frontend/package.json`: React, Vite, React
Router, Axios, Tailwind CSS, Lucide React, Recharts, and oxlint.

## Phase 5 application routes

The authenticated interface uses the backend's HttpOnly JWT cookie and CSRF
header flow through the shared Axios client. No access token is stored in
browser storage. Set `VITE_API_BASE_URL` in `frontend/.env` if the API is not
available at `http://localhost:8000/api`.

Regular user routes:

- `/app` — dashboard statistics and task status chart.
- `/tasks` — task search, status/priority/date filters, sorting, pagination,
  completion, and task actions.
- `/tasks/new`, `/tasks/:taskId`, `/tasks/:taskId/edit` — create, view, and edit
  tasks.
- `/profile` — profile and password settings.
- `/files` — private spreadsheet uploads, content search, downloads, and deletion.

Administrator routes are shown only for administrator accounts in the
navigation and are also protected by server-side RBAC:

- `/admin` — workspace statistics and recent activity.
- `/admin/users` — search, pagination, user creation, role/status management,
  viewing, and deletion.
- `/admin/tasks` — cross-user task management; administrators can also create
  and reassign tasks.

The dashboard adapts to desktop, tablet, and mobile layouts. The sidebar can
collapse on desktop and the theme toggle switches between light and dark.
Dashboard data is loaded from the
user- or administrator-scoped summary API; task and user tables use server-side
pagination and filtering.

Frontend quality checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Authentication configuration

Authentication uses short-lived JWT access tokens in `HttpOnly`, `SameSite=Lax`
cookies. The token is not exposed to JavaScript or stored in local storage.
State-changing requests use a double-submit CSRF cookie and the `X-CSRF-Token`
header. Local cookies are not `Secure` over HTTP; non-development environments
require a strong `JWT_SECRET_KEY` and use `Secure` cookies (serve the app over
HTTPS there).

Set these values in `backend/.env`:

```dotenv
APP_ENV=development
JWT_SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=15
CORS_ORIGINS=["http://localhost:5173"]
```

In development, an omitted JWT secret uses a fixed development-only key so
tokens continue to work across local reloads. Before deploying, set `APP_ENV`
to a non-development value and provide a unique secret of at least 32
characters; the API refuses to start with a missing, weak, or placeholder
production secret. Generate one in PowerShell with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The frontend sends credentials with Axios and keeps authentication state in
memory. On page reload it restores the user by calling `/api/auth/me`.

## Authentication API

- `POST /api/auth/register` — create a regular user; public admin assignment is rejected.
- `POST /api/auth/login` — authenticate and issue the HttpOnly access cookie.
- `POST /api/auth/logout` — clear authentication cookies.
- `GET /api/auth/me` — get the authenticated active user.
- `POST /api/auth/change-password` — change a password after verifying the current one; signs out.
- `GET /api/users/me` and `PATCH /api/users/me` — read or update permitted profile fields.
- `GET /api/users/admin/access` — example administrator-only access check.

Call `GET /api/auth/csrf` before a browser mutation to initialize the CSRF
cookie; the frontend does this automatically. Inactive accounts receive
`403 Forbidden`; missing or expired authentication receives `401 Unauthorized`.
Role and account status are always read from the database, not request data.

## Phase 4 task and administration APIs

Interactive API documentation is available at <http://localhost:8000/docs>
when the backend is running.

Authenticated users can manage only their own tasks:

- `GET /api/tasks` — list, search, filter, sort, and paginate tasks.
- `POST /api/tasks`, `GET /api/tasks/{task_id}`, `PATCH /api/tasks/{task_id}`,
  and `DELETE /api/tasks/{task_id}` — task CRUD.
- `GET /api/dashboard/summary` — database-backed summary for the current user.

Task list parameters include `search`, `status`, `priority`, `due_from`,
`due_to`, `overdue`, `sort_by`, `sort_direction`, `page`, and `page_size`.
Dates must include a timezone. Sorting supports `due_date`, `priority`,
`title`, and `created_at`; page size is limited to 100. Results contain
`items`, `total`, `page`, and `page_size`. A task owned by another user is
returned as `404` on user routes, regardless of the supplied task ID.

Administrators can use `/api/admin/tasks` for cross-user task CRUD, including
`owner_id` filtering and validated task creation/reassignment with `user_id`.
They can use `/api/admin/users` for searchable and paginated user management
and `GET /api/admin/dashboard/summary` for system-wide statistics. These
endpoints enforce administrator authorization on the server and record
administrative task and user mutations in `audit_logs`. The last active
administrator cannot be demoted, deactivated, or deleted.

Deleting a user cascades their database-owned tasks, tags, uploaded-file
metadata/index entries, conversations/messages, and other dependent records.
The API removes that user's private files under `backend/uploads` before
committing the database deletion; shared demo fixtures are retained. If file
cleanup fails, the database deletion is rolled back and the API reports an
error. Unsafe stored paths are rejected. Do not manually place private files
in the shared `demo-fixtures` directory.

## Phase 6 file management

The authenticated `/files` page supports private spreadsheet upload, search,
download, retry, and deletion:

- `POST /api/files/upload` — upload one `.xlsx`, `.xls`, or `.csv` file.
- `GET /api/files` — list the current user's files with pagination and optional
  extension filtering.
- `GET /api/files/{file_id}` and `GET /api/files/{file_id}/status` — retrieve
  owned-file metadata and indexing status.
- `GET /api/files/{file_id}/download` — download an owned file as an attachment.
- `DELETE /api/files/{file_id}` — remove the file and its indexed content.
- `GET /api/files/search?q=invoice%201045` — search owned filenames,
  worksheet names, and indexed cell values with source references.
- `POST /api/files/{file_id}/retry` — retry indexing for a failed owned file.

Files are private to their owner. Administrator role does not grant access to
another user's filenames, indexed content, downloads, or file IDs. Downloads
are authenticated, served as attachments with `nosniff` and sandbox headers,
and never expose server filesystem paths.

The backend stores generated, UUID-based file names beneath
`backend/uploads/user-files` by default; original names are retained only as
metadata. Set these values in `backend/.env` to change the storage root or
processing limits:

```dotenv
UPLOAD_STORAGE_DIR=uploads/user-files
FILE_MAX_SIZE_BYTES=10485760
FILE_MAX_ROWS=20000
FILE_MAX_COLUMNS=100
FILE_MAX_WORKSHEETS=20
FILE_MAX_PROCESSING_SECONDS=30
FILE_MAX_EXTRACTED_TEXT_BYTES=10485760
```

Limits apply per upload, worksheet, workbook, and indexing operation as named.
CSV input must be valid UTF-8. XLSX files are read in read-only/data-only mode;
macros and formulas are never executed. Legacy XLS parsing uses `xlrd`.
Non-empty cells are indexed as inert text with worksheet, row, and column
references. Empty values are omitted and search results are paginated. A failed
index operation keeps the uploaded file with a generic error and can be retried
from the Files page. Upload validation failures remove partial files and
metadata; deletion removes the matching index entries and stored file.

If upload returns `422`, confirm the extension and MIME type, ensure the file
is not malformed or macro-enabled, and check the configured size/row/column/
worksheet/text/time limits. If indexing fails after upload, verify that the
file is a valid spreadsheet and use **Retry indexing**. If the API cannot
create its storage directory, ensure its process account can write to the
configured `UPLOAD_STORAGE_DIR`. MySQL must be migrated to the current head
before using file APIs.

## Phase 7 chatbot

The authenticated layout includes a responsive floating assistant. It uses
deterministic request parsing and existing task CRUD and file-index search
services; no external LLM or paid API key is required. Relative dates are
interpreted with `APP_TIMEZONE` (an IANA timezone such as `UTC` or
`America/New_York`). “Today” and “tomorrow” mean the end of that local date;
task searches for “next week” cover the next Monday through Sunday. A task
creation due “next week” is ambiguous and prompts for a specific day.

Supported chat request examples:

- `Find my NLP assignment.`
- `Show my high-priority pending tasks.`
- `Which tasks are overdue?`
- `Find task ID 788.`
- `Search my Excel files for invoice number 1045.`
- `Which worksheet contains customer ABC?`
- `Create a high-priority task called Submit NLP Report, due tomorrow.`
- `Change task 25's priority to high.`
- `Delete task ID 788.`

Task creation, update, and deletion only prepare a five-minute server-side
confirmation. The assistant displays the preview and the user must explicitly
choose **Confirm**. The backend binds its opaque challenge to the authenticated
user, conversation, target, and (for existing tasks) `updated_at` version. It
rechecks authorization and record version before committing; stale previews
must be reviewed and confirmed again. Challenges are one-use, and cancelling,
expiry, replay, or a different account cannot execute the action. Admins may
search/manage tasks across users and explicitly assign new tasks to eligible
users. Chat file search follows the Phase 6 privacy policy: it searches only
the authenticated account's own uploaded files, including for administrators.

API endpoints:

- `POST /api/chat/messages` — send a message and receive bounded search results
  or an action preview.
- `GET /api/chat/conversations/{conversation_id}/messages` — retrieve the
  authenticated user's recent conversation messages.
- `POST /api/chat/actions/{challenge}/confirm` — confirm the exact prepared
  create, update, or delete.
- `DELETE /api/chat/actions/{challenge}` — cancel a pending action.

Mutations reuse the task services and are committed with chatbot audit entries.
Conversation records store the user request (with common credential patterns
redacted) and a short generic assistant response; file excerpts and opaque
confirmation challenges are not copied into conversation messages. Spreadsheet
cell values are treated as untrusted text and cannot supply commands or change
the parser's permissions. This release intentionally does not use an external
LLM; if one is added later, it must remain optional, use schema-constrained
intent output, and disclose that user prompts may be sent to the provider.

Apply the Phase 7 pending-action migration before using the chatbot:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
alembic current
```

The chatbot schema reference remains `backend/db/schema.sql`. Tests require the
separate `taskflow_test_db`; enable them only using the isolated-test settings
described above.

## Run backend tests

Tests use a dedicated MySQL database and are disabled unless explicitly enabled.
Create a separate `taskflow_test_db` database in phpMyAdmin. Apply migrations
to that test database before running tests; never point these commands at the
development database. In `backend/.env`, set `APP_ENV=development` and your
local test-database credentials (the seeder is not needed for tests). From
PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DB_NAME = "taskflow_test_db"
alembic upgrade head
$env:DB_NAME = "taskflow_db"
$env:TASKFLOW_TEST_DB_NAME = "taskflow_test_db"
$env:TASKFLOW_RUN_AUTH_TESTS = "1"
pytest -q
Remove-Item Env:TASKFLOW_TEST_DB_NAME
Remove-Item Env:TASKFLOW_RUN_AUTH_TESTS
```

`DB_NAME` is restored to the development database name before pytest so the
fixture can detect accidental targeting of the development database. Tests
connect only to `TASKFLOW_TEST_DB_NAME`; never set it equal to `DB_NAME`.
To check schema drift explicitly against the test database:

```powershell
$env:DB_NAME = "taskflow_test_db"
alembic check
$env:DB_NAME = "taskflow_db"
```

The test fixture creates any missing test tables in `TASKFLOW_TEST_DB_NAME`
and rolls back each test's data changes. It checks that this name differs from
`DB_NAME` before connecting and never targets the development database. Do not
seed this test database: several assertions intentionally expect no demo
records.

The test command reports skipped authentication tests when the opt-in
variables are absent; a skipped run is not a full passing test run.

## Database backup and reset

Before any reset, stop both application servers and make a database backup
using phpMyAdmin's **Export** tab (choose SQL) or your MySQL administrator's
backup tool. Keep a separate copy of `backend/uploads/` as it contains uploaded
file binaries that are not stored in MySQL. Verify that both backups can be
read before proceeding.

To reset a disposable local development database only, use phpMyAdmin to drop
and recreate `taskflow_db` with `utf8mb4_unicode_ci`, then, from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m db.seeders.seed_demo
```

Dropping database tables does not remove uploaded file binaries from disk.
Preserve the uploads backup and clean private files only as a separate,
intentional operation after confirming the selected storage directory. Never
reset the development database as a way to run tests; use
`taskflow_test_db` instead.

## Troubleshooting

- **MySQL connection refused:** start the local MySQL service/control panel;
  verify `Test-NetConnection 127.0.0.1 -Port 3306`; check `DB_HOST`, `DB_PORT`,
  `DB_USER`, `DB_PASSWORD`, and that `taskflow_db` exists.
- **Unknown database or missing tables:** create `taskflow_db` in phpMyAdmin
  and run `alembic upgrade head` from `backend/`.
- **Port already in use:** stop the process using port 5173 or 8000, or change
  the port and update `CORS_ORIGINS` and `VITE_API_BASE_URL` together.
- **Browser CORS error:** use the configured frontend origin consistently
  (`http://localhost:5173` by default), ensure it is present in backend
  `CORS_ORIGINS`, and restart FastAPI after changing `.env`.
- **Login or CSRF failure:** allow cookies, use the same host spelling for
  frontend/backend URLs, reload the app, and retry. Do not mix `localhost`
  with `127.0.0.1` when relying on browser cookies.
- **PowerShell blocks activation:** use
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that
  terminal, then activate the virtual environment again.
- **Upload validation/indexing error:** check supported format, file size,
  limits, MIME/signature, and write permission for `UPLOAD_STORAGE_DIR`; use
  **Retry indexing** for a retained failed upload.
- **Seeder refuses to run:** set `APP_ENV=development` in `backend/.env` or
  the current process and ensure the database is migrated. Never enable the
  development seeder in production.

## Security and known limitations

- Authentication is a short-lived JWT in an HttpOnly cookie with SameSite
  protection; mutations require a double-submit CSRF token. Role, active
  status, task ownership, and file ownership are checked on the server.
- File downloads require authentication and are returned as attachments.
  Upload files are stored under generated names; spreadsheets are parsed as
  data, not executed. Keep `backend/uploads/user-files` private and backed up.
- The assistant uses deterministic intent parsing and existing authorized
  services. It does not need an external LLM. Search results are bounded;
  task changes require short-lived, one-use confirmation and a server-side
  permission/version check.
- The seeder's published credentials are for local development only. Do not
  expose a seeded development instance to an untrusted network; change or
  remove all demo accounts before production use.
- Credential redaction in conversation history is pattern-based, not a
  guarantee against every possible secret phrasing. Do not send passwords,
  tokens, or other secrets in chat.
- The intent parser handles a bounded set of natural-language patterns.
  Ambiguous deadlines require clarification; it is not a general-purpose
  conversational model. Administrators can manage global tasks but file
  search remains owner-only.
- Production deployment needs HTTPS, a unique strong `JWT_SECRET_KEY`, secure
  cookie configuration, private MySQL credentials, storage backup/access
  controls, and an explicitly reviewed CORS allowlist. The local development
  configuration is not a production deployment profile.
