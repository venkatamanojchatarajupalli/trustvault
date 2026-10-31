# TrustVault — Secure Document Sharing and Leak Investigation

TrustVault is a secure document-sharing platform designed to protect private documents through authentication, role-based access controls, permission management, and audit logging. It helps users share documents with authorized recipients and review document-related activity.

## Live Demo

- **Frontend:** https://trustvault-beta.vercel.app/
- **Backend API:** https://trustvault-api-v92o.onrender.com
- **API documentation:** https://trustvault-api-v92o.onrender.com/docs
- **GitHub repository:** https://github.com/venkatamanojchatarajupalli/trustvault

## Features

- User registration and login
- Document upload and listing
- Document sharing with read/edit permissions
- Permission revocation
- Audit logging and activity tracking
- Incident records for document-related investigations
- FastAPI Swagger UI for exploring backend endpoints

**Current limitation:** Document downloads on the deployed application currently return a “Document file not found” error. Persistent document storage and download behavior still need to be completed and verified for production.

## Technology Stack

**Backend**
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL for the deployed database
- SQLite for the local database
- Pytest

**Frontend**
- React
- Vite
- JavaScript

## Project Structure

```text
trustvault/
├── backend/
│   ├── app/
│   ├── private_uploads/
│   ├── migrate_sqlite_to_postgres.py
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── README.md
└── README.md
```

The `private_uploads` directory and local database contain runtime data. Do not commit private documents, credentials, or secret environment files.

## Prerequisites

- Python
- Node.js and npm
- Git

## Run the Backend Locally

From the project root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The local API is available at `http://127.0.0.1:8000`.

Swagger documentation: `http://127.0.0.1:8000/docs`

Configure any required environment variables before running in a fresh environment. Do not publish database URLs, passwords, secret keys, or other credentials.

## Run the Frontend Locally

Open a second PowerShell terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. Keep the backend running while testing the frontend.

## Run Backend Tests

From the project root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Security and Deployment Notes

- Use strong secret keys and keep credentials out of version control.
- Configure production CORS, HTTPS, authentication, and access controls appropriately.
- Store uploaded documents in persistent, access-controlled storage for production use.
- Verify document downloads and permissions in the deployed environment.
- Never commit private uploaded files, local databases containing user data, or environment files.

## Project Goal

TrustVault aims to provide secure document sharing with controlled access, traceable activity, and support for investigating document-related incidents.

## Current Status

The frontend and backend are deployed, and the deployed admin login and dashboard have been verified. The local SQLite data was migrated to PostgreSQL, with row counts verified across five tables. Some production behavior, including document downloads and persistent file storage, remains unfinished.
