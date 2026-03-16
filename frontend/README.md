# Frontend Setup & Execution Guide

This guide explains how to set up and run the `frontend` package alongside the Python backend to ensure all parts of the application communicate correctly.

## Architecture Overview

The application is split into three main services that must run concurrently:

1. **Python Backend (Story Engine):** A FastAPI server managing the core narrative logic.
2. **Frontend Server (BFF):** A Node.js Express server handling Google Cloud Vertex AI (Reasoning Engine) and Imagen requests.
3. **Frontend Client:** A React (Vite) application that serves the UI.

The Vite client is configured to proxy API requests to both servers:
- `/api/story/generate-image` and `/api/agent` → **Frontend Server** (`localhost:3001`)
- All other `/api/*` requests → **Python Backend** (`localhost:8000`)

---

## Prerequisites

- **Node.js** (v18 or higher)
- **Python** (3.11+) and [uv](https://github.com/astral-sh/uv)
- **Google Cloud CLI** (`gcloud`) installed and configured.

---

## 1. Environment Configuration

### Frontend Server `.env`
Create a `.env` file inside the `frontend/server/` directory with the following variables:

```env
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_REASONING_ENGINE_ID=your_engine_id
PORT=3001
```

### Python Backend `.env`
Ensure you also have your `.env` configured at the **root** of the repository for the Python backend:

```env
GEMINI_API_KEY=your_gemini_api_key
```

### Google Cloud Authentication
The Frontend Server uses Application Default Credentials to call Vertex AI. Authenticate your local environment by running:

```bash
gcloud auth application-default login
```

---

## 2. Running the Stack

You will need **three separate terminal windows** to run the complete stack.

### Terminal 1: Python Backend
Start the core Story Engine API from the **root directory** of the project:

```bash
# Install dependencies (if not already done)
uv sync

# Start the FastAPI server
uv run uvicorn story_engine.main:app --reload
```
*Server runs on `http://localhost:8000`*

### Terminal 2: Frontend Server (BFF)
Start the Node.js backend for handling image generation and Vertex AI requests:

```bash
cd frontend/server
npm install
npm run dev
```
*Server runs on `http://localhost:3001`*

### Terminal 3: Frontend Client
Start the Vite React application:

```bash
cd frontend/client
npm install
npm run dev
```
*App runs on `http://localhost:5173`*

---

## Verification

Once all three processes are running, open your browser and navigate to **http://localhost:5173**. The client will now be able to communicate seamlessly with both the Python and Node.js backends.
