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

The initial skeleton should run without a real camera or AI model.

Use:

- Fake detections.
- Fake traffic state.
- Fake frame placeholder.
- Hard-coded zones.

Then gradually replace fake parts with real camera and model code.

## Git workflow suggestion

For the existing GitHub repo, use these commit messages when applying patches manually through the GitHub website:

```text
Initial project skeleton v0_0_0
Fix documentation versioning v0_0_1
```

Recommended branch names later:

```text
main
dev
feature/live-view
feature/yolo-detection
feature/zone-counting
feature/esp-cam-stream
feature/dataset-capture
```
