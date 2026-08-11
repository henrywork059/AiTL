# Start Test-Ready 0_1_0 on Windows

Open two Command Prompt windows.

## Window 1 — backend

```bat
scripts\start_pc_studio_backend_windows.bat
```

Wait until the terminal shows Uvicorn running on `http://127.0.0.1:8000`.

Check:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/smoke/status
```

## Window 2 — frontend

```bat
scripts\start_pc_studio_frontend_windows.bat
```

Open:

```text
http://localhost:5173
```

## Optional backend smoke test

Open a third Command Prompt window:

```bat
scripts\test_backend_smoke_windows.bat
```

The expected result is all listed endpoints showing `PASS`.
