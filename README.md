# Skin AI Assistant

A full-stack web app that analyzes a skin photo and an optional blood report to suggest a personalized skincare routine. It uses a placeholder skin classifier, OCR (pytesseract) for lab values, and a rule-based recommendation engine. **This is not medical advice**; the app includes visible disclaimers.

---

## 1. Folder tree

```
skin-ai-app/
├── main.py                 # Entry point: uvicorn main:app --reload
├── requirements.txt        # Python backend dependencies
├── README.md               # This file
├── .gitignore
│
├── backend/
│   ├── main.py             # FastAPI app, CORS, router
│   ├── config.py           # Settings (file limits, allowed types)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # POST /api/analyze, GET /api/health
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── skin_classifier.py   # Placeholder skin analysis from image
│   │   ├── ocr_extractor.py     # pytesseract OCR (image + PDF)
│   │   ├── lab_parser.py        # Structured lab value parser
│   │   └── recommendation_engine.py  # Rule-based routine + explanation
│   ├── services/
│   │   ├── __init__.py
│   │   └── analysis_service.py # Orchestrates pipeline
│   └── utils/
│       ├── __init__.py
│       ├── validation.py       # File size/type validation
│       └── logging_config.py   # Logging setup
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js         # Proxy /api -> backend
    └── src/
        ├── main.jsx
        ├── App.jsx             # Routes: /, /results
        ├── index.css           # Global styles
        ├── api/
        │   └── client.js       # analyzeSkin(), healthCheck()
        ├── components/
        │   ├── Layout.jsx      # Header, main, disclaimer, footer
        │   ├── Layout.module.css
        │   ├── Disclaimer.jsx  # Visible “not medical advice”
        │   └── Disclaimer.module.css
        └── pages/
            ├── HomePage.jsx    # Upload form, loading, error
            ├── HomePage.module.css
            ├── ResultsPage.jsx # Analysis + routine + disclaimer
            └── ResultsPage.module.css
```

---

## 2. Backend code (overview)

- **`main.py`** (root): Imports `app` from `backend.main` so you can run `uvicorn main:app --reload` from project root.
- **`backend/main.py`**: Creates FastAPI app, adds CORS, mounts `/api` routes.
- **`backend/config.py`**: Pydantic settings for max file sizes (e.g. 5 MB skin, 10 MB report), allowed MIME types.
- **`backend/api/routes.py`**: `GET /api/health`, `POST /api/analyze` (multipart: `skin_image` required, `blood_report` optional). Validates files then calls analysis service.
- **`backend/services/analysis_service.py`**: Runs skin classifier → optional OCR → lab parser → recommendation engine; returns one JSON result.
- **`backend/utils/validation.py`**: Validates size and format (magic bytes for images/PDF); blocks path traversal in filenames.
- **`backend/utils/logging_config.py`**: Configures root logger and format.

---

## 3. Frontend code (overview)

- **`frontend/src/App.jsx`**: React Router with `/` (HomePage) and `/results` (ResultsPage).
- **`frontend/src/components/Layout.jsx`**: Wraps all pages with header, main content, **Disclaimer** block, and footer.
- **`frontend/src/components/Disclaimer.jsx`**: Visible disclaimer that the app is not medical advice.
- **`frontend/src/pages/HomePage.jsx`**: Form for skin image (required) and blood report (optional); calls `analyzeSkin()`, shows loading/error, navigates to `/results` with result in `location.state`.
- **`frontend/src/pages/ResultsPage.jsx`**: Reads `location.state.result`; shows skin analysis, lab values (if any), routine (AM/PM), lab notes, and disclaimer.
- **`frontend/src/api/client.js`**: `analyzeSkin(skinFile, bloodReportFile)` and `healthCheck()`; uses `/api` so Vite proxy forwards to backend in dev.

---

## 4. AI modules (overview)

- **`skin_classifier.py`**: Placeholder. Opens image with PIL, computes simple color/brightness stats, maps heuristically to `skin_type` (e.g. dry, oily, normal, sensitive) and `conditions`. Returns `explanation` for explainability. Replace with a real CV/ML model for production.
- **`ocr_extractor.py`**: Uses `pytesseract` to get text from image bytes; for PDFs uses `pdf2image` to render pages then OCR. `extract_text_from_blood_report(content, is_pdf)` dispatches to the right path.
- **`lab_parser.py`**: Regex-based parser on OCR text for markers like Vitamin D, ferritin, Hb, TSH, B12, zinc, etc. Extracts numeric values and units; returns `values` dict and `raw_snippets` for debugging.
- **`recommendation_engine.py`**: Rule-based. Takes `skin_result` and `lab_result`; builds AM/PM routine (cleanser, antioxidant, moisturizer, sunscreen; PM: cleanser, treatment, moisturizer) and adds lab-based notes (e.g. low Vitamin D). Returns `routine`, `explanation`, `lab_notes`, and a **disclaimer** string.

---

## 5. Installation steps

1. **Clone or copy** the project into a folder (e.g. `skin-ai-app`).

2. **Python (backend)**  
   - Use Python 3.10+.
   - Create and activate a virtual environment:
     ```bash
     python -m venv .venv
     .venv\Scripts\activate   # Windows
     # source .venv/bin/activate   # Linux/macOS
     ```
   - From the **project root** (`skin-ai-app`):
     ```bash
     pip install -r requirements.txt
     ```

3. **Tesseract OCR**  
   - Required for blood report text extraction.
   - **Windows**: Install from [Tesseract at GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH, or set in code:
     ```python
     # In backend/ai/ocr_extractor.py (optional)
     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
     ```
   - **Linux**: `sudo apt install tesseract-ocr`
   - **macOS**: `brew install tesseract`

4. **PDF support (optional)**  
   - For PDF blood reports, `pdf2image` needs **poppler**:
     - Windows: e.g. `choco install poppler`
     - Linux: `sudo apt install poppler-utils`
     - macOS: `brew install poppler`

5. **Node (frontend)**  
   - Install Node 18+ and npm.
   - From project root:
     ```bash
     cd frontend
     npm install
     ```

---

## 6. Run steps

Run **from the project root** (`skin-ai-app`).

1. **Start backend**
   ```bash
   uvicorn main:app --reload
   ```
   - API: http://127.0.0.1:8000  
   - Docs: http://127.0.0.1:8000/docs  

2. **Start frontend** (new terminal)
   ```bash
   cd frontend
   npm run dev
   ```
   - App: http://localhost:3000  
   - Vite proxies `/api` to the backend.

3. **Use the app**
   - Open http://localhost:3000.
   - Upload a skin photo (required) and optionally a blood report (PDF or image).
   - Click “Analyze”; wait for loading; view results and disclaimer on the results page.

---

## 7. Deployment guide

- **Backend**
  - Run with a production ASGI server, e.g. `uvicorn main:app --host 0.0.0.0 --port 8000` (no `--reload`).
  - Set `LOG_LEVEL` if needed.
  - Use a reverse proxy (e.g. Nginx) for HTTPS and to forward `/api` to the backend.
  - Optionally set file limits and CORS `allow_origins` via env or `config.py`.

- **Frontend**
  - Build: `cd frontend && npm run build`.
  - Serve `frontend/dist` with Nginx or any static host.
  - Set API base URL: either keep relative `/api` and proxy from the same host, or set `VITE_API_URL` and use it in `api/client.js` for `fetch(API_BASE + ...)`.

- **Security**
  - File validation (size, type, filename) is in `backend/utils/validation.py`; adjust limits in `config.py`.
  - Do not store uploaded files unless needed; current flow processes in memory and does not persist.
  - Restrict CORS `allow_origins` in production to your frontend origin.

- **Disclaimer**
  - The app shows a visible disclaimer that it is not medical advice; keep it on all pages and in the API response text.

---

## Comments summary

- **Config**: Centralized in `backend/config.py` for limits and types.
- **Validation**: Protects against oversized uploads, wrong formats, and path traversal.
- **Pipeline**: Skin image → placeholder classifier; optional report → OCR → lab parser; both → recommendation engine → single JSON.
- **Frontend**: Upload form with loading/error; results page shows analysis, routine, and disclaimer; layout includes a persistent disclaimer component.
- **Runnable locally** with `uvicorn main:app --reload` from project root and frontend at `http://localhost:3000`.
