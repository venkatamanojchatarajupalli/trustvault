# TrustVault — Secure Document Sharing and Leak Investigation

TrustVault is a secure document-sharing platform designed to protect private documents through authentication, access controls, and audit logging. It helps users share documents with authorized recipients and investigate document-related activity.

## Features

- **User authentication:** Register and log in securely.
- **Document management:** Upload, list, view, and download documents.
- **Access control:** Share documents with specific users and control read/edit permissions.
- **Permission revocation:** Revoke previously granted document access.
- **Audit logging:** Record document-related actions for accountability and investigation.
- **Activity tracking:** Review recorded activities through the application interface.
- **API documentation:** Explore and test backend endpoints using FastAPI Swagger UI.

## Technology Stack

**Backend**
- Python
- FastAPI
- SQLAlchemy
- SQLite
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
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── README.md
└── README.md
```

The `private_uploads` directory and local database contain runtime data and should not be committed to the public repository.

## Prerequisites

- Python installed
- Node.js and npm installed
- Git installed

## Run the Backend Locally

Open PowerShell in the project directory and run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The backend API will be available at:

- API base URL: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs

Create and configure the required environment variables before running the application in a fresh environment. Never commit actual secret keys or credentials.

## Run the Frontend Locally

Open a second PowerShell terminal and run:

```powershell
cd frontend
$env:Path = "C:\Program Files\nodejs;$env:Path"
& "C:\Program Files\nodejs\npm.cmd" run dev
```

Open the local URL printed by Vite in the terminal. In the current development setup, the frontend runs at:

http://localhost:5175/

Keep the backend running while using the frontend.

## Run Backend Tests

From the project root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Security Notes

- Keep environment files, secret keys, local databases, virtual environments, and private uploaded documents out of version control.
- Use a strong, unique secret key in each deployment environment.
- Configure production CORS, HTTPS, authentication, and storage permissions appropriately before public deployment.
- Ensure uploaded documents are stored in persistent, access-controlled storage in production.
- Do not use development server settings as a substitute for production deployment configuration.

## Current Status

The project has a working local backend and frontend, including document management, sharing permissions, access revocation, and activity/audit views. Public production deployment and its storage configuration must be verified separately.

## Project

**Name:** TrustVault — Secure Document Sharing and Leak Investigation

**Goal:** Provide secure document sharing with controlled access, traceable activity, and support for investigating document-related incidents.
