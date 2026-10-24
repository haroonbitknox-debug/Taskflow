# TaskFlow

TaskFlow is a local full-stack task-management application with a React/Vite
frontend, FastAPI backend, and PostgreSQL database (including Neon). It
includes cookie-based authentication, role-based access control, task and user
management, private
spreadsheet upload/index/search, dashboards, and a chatbot that requires
explicit confirmation before it changes tasks.

## Prerequisites

- Windows 10/11 and VS Code with PowerShell
- Python 3.10 or newer and `py` (the tested environment uses Python 3.12)
- Node.js 20.19 or newer and npm
- A PostgreSQL database such as Neon, or local PostgreSQL for development

The application uses SQLAlchemy with psycopg. The optional one-time MariaDB
data-copy utility uses PyMySQL; it does not change the source database.

## Local setup and startup

### 1. Create a Neon database

Create a Neon project and database in the Neon console. Use the pooled
connection string for application traffic and the direct connection string for
migrations/admin tasks. The backend loads `backend/.env` and the root
`.env.local`; process environment variables take precedence over both.
`neon deploy` can populate the root `.env.local` with `DATABASE_URL` and
`DATABASE_URL_UNPOOLED`. The configuration upgrades Neon `sslmode=require` to
`verify-full`, using the `certifi` root CA bundle when no custom certificate
path is specified; certificate and hostname verification remain enabled.

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

When using Neon CLI, keep its generated `.env.local` private and do not copy
credentials into frontend files. Otherwise, set `DATABASE_URL` in
`backend/.env`; set `DATABASE_URL_UNPOOLED` there as well when using a distinct
direct URL for migrations. Keep both files private. For local PostgreSQL only, a local URL may use
`sslmode=disable`; non-local databases always use verified TLS. The checked-in
`.env.example` contains placeholders. The development configuration has a
development-only fallback JWT key. For a local custom key, generate one with
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
on an exposed or production installation. Do not run the seeder against the
dedicated test database; the automated test suite expects it to remain clean.

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
Uvicorn, SQLAlchemy, Pydantic Settings, Alembic, psycopg, PyMySQL (legacy-data
migration only), Argon2, PyJWT,
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
- `POST /api/auth/password-reset/request` — request email reset instructions without revealing whether the account exists.
- `POST /api/auth/password-reset/confirm` — set a new password using a valid, single-use reset token.
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
configured `UPLOAD_STORAGE_DIR`. Apply the current Alembic migrations before
using file APIs.

## Phase 7 chatbot

The authenticated layout includes a responsive floating assistant. It uses
deterministic request parsing and existing task CRUD services. Spreadsheet
questions use OpenRouter's Chat Completions API to interpret a restricted query
plan and summarize results from the authenticated user's existing file index.
Spreadsheet filtering and calculations run in the backend; the model never
receives unrestricted database access. Relative dates are interpreted with
`APP_TIMEZONE` (an IANA timezone such as `UTC` or `America/New_York`). “Today”
and “tomorrow” mean the end of that local date; task searches for “next week”
cover the next Monday through Sunday. A task creation due “next week” is
ambiguous and prompts for a specific day.

Configure OpenRouter in `backend/.env`:

```dotenv
OPENROUTER_API_KEY=your_server_side_key
OPENROUTER_MODEL=your_selected_model_id
OPENROUTER_TIMEOUT_SECONDS=30
OPENROUTER_MAX_TOKENS=1200
```

Choose a model ID that is currently available to your OpenRouter account; the
project does not select a default model or assume that a model is free. Review
the model's provider, data handling, context/token limits, and pricing before
use. Spreadsheet prompts (with common credential patterns redacted), column
names, and only matching row data are sent to OpenRouter for interpretation or
answer generation. The backend returns clear
errors when configuration is missing or the provider fails; it does not
generate a fallback answer. Keep the key only in the backend environment:
never add it to frontend `VITE_` variables, browser storage, source control, or
client responses. The checked-in `.env.example` contains blank placeholders.
`httpx` is already a backend dependency and is reused by the integration.
If a request fails, the backend log records only the upstream status, configured
model ID, provider error code when supplied, and a sanitized provider message.
The API returns a safe category-specific explanation instead of provider
details or stack traces. Authentication, account-credit, permission, invalid
model/request, rate-limit, and provider-server failures have distinct messages;
check backend logs for the corresponding diagnostic category. Spreadsheet
values and the OpenRouter key are redacted from logged provider errors.

For a backend-only test run that does not require PostgreSQL or paid API calls:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests\test_spreadsheet_chat_service.py
```

Supported chat request examples:

- `Find my NLP assignment.`
- `Show my high-priority pending tasks.`
- `Which tasks are overdue?`
- `Find task ID 788.`
- `Search my Excel files for invoice number 1045.`
- `Show high-priority projects that are still pending.`
- `How many pending records?`
- `Sum Amount for pending projects.`
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
redacted) and a short assistant response; file excerpts and opaque confirmation
challenges are not copied into conversation messages. Spreadsheet cell values
are treated as untrusted text and cannot supply commands or change the parser's
permissions. The model can select only validated filter and calculation
operations. The backend derives the user identity from the existing
authentication dependency, scopes every index query to that user, and returns
source filenames, worksheets, and row references when available. Results are
bounded; questions exceeding the safe retrieval limit ask for narrower filters.
Task creation, updates, and deletions remain deterministic, use existing task
services, and still require explicit confirmation.

Apply the Phase 7 pending-action migration before using the chatbot:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
alembic current
```

The schema is managed by Alembic. Tests require a separate PostgreSQL database;
enable them only using the isolated-test settings
described above.

Spreadsheet answers include source cards in the chat for matching rows. Manual
UI checks after configuration:

1. Ask `Show high-priority projects that are still pending.` and verify only
   matching rows appear with their source filename, worksheet, and row.
2. Ask for a pending-record count and a sum over a numeric column; compare the
   results with the uploaded sheet.
3. Ask about a column that does not exist and verify the assistant reports the
   missing field instead of guessing.
4. Put instruction-like text in a spreadsheet cell and verify it is treated as
   cell content, not followed.
5. Try an unavailable model or unset the backend key and verify an explicit
   error appears while ordinary task search and confirmation still work.

## Run backend tests

Password recovery and spreadsheet chat tests use isolated in-memory SQLite
databases and mocked email/provider calls. The optional broader integration
suite uses a separate PostgreSQL test database and is disabled unless enabled
explicitly. Never run it against the development or production database. From
PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:TASKFLOW_TEST_DATABASE_URL = "postgresql://USER:PASSWORD@HOST/taskflow_test?sslmode=require"
$env:DATABASE_URL = $env:TASKFLOW_TEST_DATABASE_URL
alembic upgrade head
$env:TASKFLOW_RUN_AUTH_TESTS = "1"
pytest -q
Remove-Item Env:TASKFLOW_TEST_DATABASE_URL
Remove-Item Env:TASKFLOW_RUN_AUTH_TESTS
```

The test fixture refuses to run if the test URL equals the configured
application database. To check schema drift, set `DATABASE_URL` to the
dedicated test database and run:

```powershell
alembic check
```

The fixture creates test tables and rolls back each test's data changes. Do not
seed the test database: several assertions intentionally expect no demo data.

The test command reports skipped authentication tests when the opt-in
variables are absent; a skipped run is not a full passing test run.

## MariaDB to Neon data migration

The source MariaDB instance was not reachable during preparation (no process
was listening on port 3306). The pasted XAMPP log also shows Aria recovery and
`mysql.plugin` initialization failures, so **no source export or data migration
has been performed**. The provided copy utility reads from MariaDB and writes
to an empty PostgreSQL database only after migrations have been applied. It checks
all TaskFlow table counts, lets PostgreSQL enforce foreign keys, and updates
generated-ID sequences. It refuses to write if the target is not empty.

Never delete, replace, or attempt recovery directly inside
`C:\xampp\mysql\data`. First stop MySQL and make a separate, complete copy of
that directory. If you later recover the original server, create a logical
backup before migration (run from PowerShell; keep the dump private):

```powershell
New-Item -ItemType Directory -Path 'D:\Backups' -Force | Out-Null
& 'C:\xampp\mysql\bin\mysqldump.exe' --single-transaction --routines --triggers --events --default-character-set=utf8mb4 -h 127.0.0.1 -P 3306 -u root -p taskflow_db --result-file='D:\Backups\taskflow-mariadb.sql'
```

If the export succeeds, keep it as a rollback/archive artifact. To copy the live
source rows into Neon, first apply the PostgreSQL schema to an empty target and
run the read-only source-to-target copier from `backend/`:

```powershell
$env:DATABASE_URL = 'postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require'
$env:SOURCE_DATABASE_URL = 'mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/taskflow_db?charset=utf8mb4'
alembic upgrade head
python -m scripts.migrate_mysql_to_postgres --dry-run
python -m scripts.migrate_mysql_to_postgres
Remove-Item Env:SOURCE_DATABASE_URL
```

Use URL-encoded credentials if a password contains URL-reserved characters.
The copy utility does not read the SQL dump; it requires the source MariaDB
server to be running and its source URL to be available. `--dry-run` checks
source tables, reports source row counts, and confirms target tables are empty
without copying anything. The real run is one PostgreSQL transaction; row-count
or relationship failures roll it back. Uploaded file binaries are not in the
database: also copy `backend/uploads/user-files` to the deployment's configured
storage, preserving paths and access controls. Reconcile important records
and keep both the SQL export and the original MariaDB files until application
behavior and counts are verified.

## Password recovery and email delivery

The sign-in page links to `/forgot-password`; reset links point to
`APP_BASE_URL/reset-password`. The API stores only a hash of the random,
single-use token, expires it after `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, and
uses database-backed request and IP rate limits. Unknown and known email
addresses receive the same response. Requests require a configured mail
provider: set `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
`MAIL_FROM`, and `APP_BASE_URL` in the backend environment. STARTTLS with
certificate verification is enabled by default on port 587. For implicit TLS
providers, set `MAIL_USE_SSL=true` and `MAIL_STARTTLS=false`. These mail values
are server-only; never add them to `frontend/.env`.

For local testing, configure a development SMTP account/provider and
`APP_BASE_URL=http://localhost:5173`, then request a reset for a test user.
Without a configured provider the endpoint returns a configuration error; a
successful response is not evidence of inbox delivery. Provider delivery
failures are recorded in backend logs without logging the email or token.

## Neon and SaaS deployment

1. Create a Neon project and database. Use its pooled connection string for
   `DATABASE_URL` and its direct connection string for
   `DATABASE_URL_UNPOOLED`.
2. Set both values as backend secrets in your host (never as
   `VITE_DATABASE_URL`). It may use Neon’s `sslmode=require`; TaskFlow upgrades
   it to `verify-full`. Set `APP_ENV=production`, a strong unique
   `JWT_SECRET_KEY`, `APP_BASE_URL` to the trusted HTTPS frontend origin,
   `CORS_ORIGINS` to that origin, and all `MAIL_*` values.
3. Build/install the backend from `backend/`, run `alembic upgrade head` as a
   deployment release step, and start `uvicorn app.main:app --host 0.0.0.0
   --port $PORT` using the host's required port syntax.
4. Set `VITE_API_BASE_URL` to the public HTTPS API URL before running
   `npm run build` in `frontend/`; serve the generated `frontend/dist` files.
5. Verify `/api/health`, registration/sign-in, password reset delivery, file
   storage, and core task flows in the deployed environment.

The current upload backend writes to `UPLOAD_STORAGE_DIR`; configure persistent
storage for a single API instance, or add a shared/object-storage adapter before
running multiple API replicas.

This version models personal accounts and scopes normal user task, file, and
chat access by authenticated user ID. It does not define shared workspaces,
teams, or workspace membership; administrator endpoints intentionally provide
cross-account administration. Add an explicit workspace/membership model and
scope every tenant-facing query before offering shared multi-user workspaces.
The current model therefore provides per-account isolation, not complete
workspace-level multi-tenancy.

## Troubleshooting

- **PostgreSQL connection refused:** confirm the Neon endpoint and
  `DATABASE_URL`, and verify the backend hosting region/network can reach it.
- **Unknown database or missing tables:** verify the Neon database exists and
  run `alembic upgrade head` from `backend/`.
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
  cookie configuration, private database credentials, storage backup/access
  controls, and an explicitly reviewed CORS allowlist. The local development
  configuration is not a production deployment profile.
