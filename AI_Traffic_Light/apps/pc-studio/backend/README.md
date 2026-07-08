# PC Studio Backend

Python/FastAPI backend placeholder for the PC Studio App.

## Current state

This version serves mock data only.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/mock/frame
http://127.0.0.1:8000/api/traffic/state
```

## Later backend modules

- camera input service
- YOLO detection service
- zone counting service
- traffic decision engine
- dataset capture service
- model training/export service
