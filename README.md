# MovieBot — Run Guide

Short instructions to generate the JSON dataset, run the Flask GraphQL backend and the Streamlit frontend on Windows.

## Prerequisites
- Python 3.9+
- PowerShell or cmd
- (Optional) Ollama or any LLM service if you want natural-language → GraphQL conversion via `/chatbot`

## Install dependencies
Open PowerShell in the project root:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Prepare dataset (CSV → JSON)
If you have `data\imdb.csv` run:

```powershell
python data\csv_to_json.py
```

This produces `data\imdb.json`. The backend expects `imdb.json` in its working directory (`backend\imdb.json` by default). Move or copy the file:

```powershell
copy data\imdb.json backend\imdb.json
```

If you prefer, edit `backend\app.py` and set `DATA_FILE` to the path `data\imdb.json`.

Note: Ensure empty CSV fields are converted to JSON nulls. If needed, update `csv_to_json.py` to replace NaN with None before saving (pandas -> dict -> json).

## Run backend (Flask + Ariadne)
Start the backend from project root:

```powershell
python backend\app.py
```

- GraphQL playground (GET): http://127.0.0.1:5000/graphql
- GraphQL endpoint (POST): http://127.0.0.1:5000/graphql
- Chatbot endpoint (POST): http://127.0.0.1:5000/chatbot

Example GraphQL POST (curl / PowerShell):

```powershell
curl -X POST http://127.0.0.1:5000/graphql -H "Content-Type: application/json" -d "{\"query\":\"query{ listMovies(limit:3){ Title Year Rating } }\"}"
```

## Run frontend (Streamlit)
Start the Streamlit UI:

```powershell
streamlit run frontend\app.py
```

The UI will call the backend `/chatbot` endpoint for NL → GraphQL flow (if available) or can call `/graphql` directly.

## Ollama model configuration (LLM)
The backend uses Ollama in `backend/app.py`. The request payload sets a `model` field. In the shipped code the example model is:

- qwen2.5:1.5b

You can use any model supported by your LLM service by changing the `"model"` value in the `api_payload` inside `backend/app.py`. Example section in `backend/app.py`:

```python
api_payload = {
    "model": "qwen2.5:1.5b",   # <-- change this to any available model name
    "messages": [{"role": "user", "content": prompt}],
    "stream": False,
    "options": {"temperature": 0}
}
```

Any valid model identifier for your LLM service may be used (replace `"qwen2.5:1.5b"` with the desired model). If Ollama is not running, `/chatbot` will fail — either run Ollama locally or call the GraphQL endpoint directly.

## Troubleshooting
- Missing `imdb.json`: run csv_to_json.py and copy file to backend folder or edit `DATA_FILE`.
- Empty values not null: ensure CSV NaN values are converted to None before JSON serialization.
- Ollama connect error: ensure Ollama runs on `127.0.0.1:11434` or change `OLLAMA_API_URL` in `backend/app.py`.
- Change backend port: edit `app.run(...)` in `backend/app.py`.

## File map
- backend\app.py — Flask + Ariadne GraphQL server and `/chatbot` LLM proxy
- frontend\app.py — Streamlit UI
- data\csv_to_json.py — CSV → JSON converter
- requirements.txt — Python deps
