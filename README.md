# ADINN OOH Site Tracker - Neon PostgreSQL Version

A responsive internal web application for tracking OOH hoarding sites, landlord details, photos/documents, GPS, agreement dates, section-wise remarks, and admin-controlled CRUD permissions.

## Current stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: Neon PostgreSQL
- ORM: SQLAlchemy
- Uploads: Local `backend/app/uploads/` folder, or Render Persistent Disk in production

## What Neon stores

Neon PostgreSQL stores structured app data:

- users
- employee/admin login details
- employee active/blocked status
- employee CRUD permission
- OOH site records
- landlord details
- size, rental, light, side, direction
- GPS latitude/longitude
- agreement dates
- section-wise remarks
- file path references for uploaded photos/documents

Photos and documents are **not stored inside Neon**. They are saved as files in the uploads folder, and Neon stores only their path/reference.

## Upload storage

Local development:

```text
backend/app/uploads/
```

Production on Render with Persistent Disk:

```text
/var/data/uploads
```

Set this in backend environment variables:

```text
UPLOAD_DIR=/var/data/uploads
```

## Neon setup

1. Create a Neon project.
2. Create or use the default database.
3. Copy the connection string from Neon Dashboard > Connect.
4. Use the pooled or direct connection string with `sslmode=require`.

Example:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

The backend automatically converts `postgresql://` into SQLAlchemy's `postgresql+psycopg://` format internally.

## Backend setup

```bash
cd backend
python3.14 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and paste your Neon connection string:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
OOH_SECRET_KEY=change-this-secret-before-production
SEED_ADMIN_EMAIL=admin@adinn.com
SEED_ADMIN_PASSWORD=Admin@123
```

Run backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok","database":"neon-postgresql"}
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Default login

If you keep the default `.env` seed values:

```text
Admin Email: admin@adinn.com
Admin Password: Admin@123
```

For deployment, change the admin password before first public use.

## Deployment notes

Backend service environment variables:

```text
DATABASE_URL=your_neon_connection_string
OOH_SECRET_KEY=long_random_secret
SEED_ADMIN_EMAIL=admin@adinn.com
SEED_ADMIN_PASSWORD=strong_password
CREATE_DEMO_EMPLOYEE=false
CORS_ORIGINS=https://your-frontend-domain.com
UPLOAD_DIR=/var/data/uploads
```

Frontend environment variable:

```text
VITE_API_URL=https://your-backend-domain.com
```

Frontend build command:

```bash
npm install && npm run build
```

Publish directory:

```text
dist
```

Backend start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Migrating old MongoDB data

If you already entered data in the MongoDB version, you can migrate the metadata to Neon:

```bash
cd backend
source venv/bin/activate
python scripts/migrate_mongodb_to_neon.py
```

Before running the migration, temporarily add your old MongoDB connection details to `.env`:

```text
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=adinn_ooh_tracker
```

Uploaded files are not inside MongoDB. Copy this folder separately:

```text
backend/app/uploads/
```

## Backup

To fully back up the app:

1. Export/backup the Neon PostgreSQL database.
2. Copy the uploads folder.

Both are needed because Neon stores metadata and the uploads folder stores actual photos/documents.
