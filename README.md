# AutoAPI Intelligence (SENTINEL-API)

AutoAPI Intelligence is an automated API testing and analysis platform powered by LangGraph. It provides a visual dashboard to manage reports, a rich frontend for dropping OpenAPI specs or GitHub URLs, and a powerful CLI.

## Prerequisites
- Node.js (v18+)
- Python 3.10+
- SQLite (for the database, handled automatically)

---

## 🚀 1. Running the Backend Server (FastAPI)

The backend handles the AI pipeline, analysis, database persistence, and authentication.

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(We recommend using a virtual environment like `venv` or `conda`).*

2. **Set up Environment Variables:**
   Make sure you have your keys exported. Examples:
   ```bash
   export OPENAI_API_KEY="your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"
   ```

3. **Start the API Server:**
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
   The backend will be running at `http://localhost:8000`. 
   Swagger documentation is available at `http://localhost:8000/docs`.

---

## 🌐 2. Running the Frontend Website (Next.js)

The frontend contains the landing page, dashboard, and the OpenAPI specification drag-and-drop feature.

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **Start the Development Server:**
   ```bash
   npm run dev
   ```
   The website will be running at `http://localhost:3000`.

---

## 💻 3. Using the Command Line Interface (CLI)

The project also comes with a CLI for analyzing APIs directly from your terminal.

**Usage:**
```bash
python -m backend.cli.main --file path/to/openapi.yaml
```

**Analyze a GitHub URL:**
```bash
python -m backend.cli.main --file "https://github.com/user/repo/blob/main/openapi.yaml"
```

*Note: For the CLI to work, make sure your Python environment has all dependencies installed via `requirements.txt` and your API keys are exported.*

---

## Project Structure
- `app/`: Next.js frontend code (Pages, Components)
- `backend/`: FastAPI server, CLI, LangGraph pipelines, and Models
- `vscode-extension/`: VS Code Extension plugin codebase
