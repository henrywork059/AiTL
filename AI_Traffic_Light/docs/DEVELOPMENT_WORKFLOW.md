# Development Workflow

## GUI hot preview

Use Vite for the frontend.

```bash
cd apps/pc-studio/frontend
npm install
npm run dev
```

Change a `.tsx` or `.css` file. The browser should update immediately.

## Backend reload

Use FastAPI with uvicorn reload.

```bash
cd apps/pc-studio/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS/Linux:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Mock-first development

The first version should run without a real camera or AI model.

Use:

- Fake detections.
- Fake traffic state.
- Fake frame placeholder.
- Hard-coded zones.

Then gradually replace fake parts with real camera and model code.

## Git workflow suggestion

```bash
git init
git add .
git commit -m "Initial AI traffic light project skeleton"
```

Recommended branch names:

```text
main
dev
feature/live-view
feature/yolo-detection
feature/zone-counting
feature/esp-cam-stream
feature/dataset-capture
```
