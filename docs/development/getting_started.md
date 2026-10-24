# Development Guide — FDR Sentinel

## Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- Node.js 18+ (Node.js v22 compatible)
- PowerShell (Windows) or Bash

## Quick Start

### 1. Setup Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python scripts/init_db.py
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Setup Frontend
```powershell
cd frontend
npm install
npm run dev
```

### 3. Run Automated Tests
```powershell
# From project root
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```
