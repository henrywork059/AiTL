# Patch 0_4_8 — System-Python child under verified AiTL Uvicorn launcher

Candidate `0_4_8`; previous candidate `0_4_7`; owner-confirmed baseline `0_4_0`.

The Windows process trace confirms that the listener PID 35864 uses system Python, while its direct parent PID 35220 runs `uvicorn app.main:app --reload --port 8000` using AiTL's backend virtualenv Python. V0407 rejected the child because it required the listener executable to be the virtualenv Python binary.

V0408 accepts a Python child with the expected Uvicorn application/port command or multiprocessing spawn command only if the direct parent runs the matching Uvicorn reload command from this project's virtualenv. The process tree root stays at the verified virtualenv launcher; PowerShell and unrelated processes are protected.

The updater safety regression now tests this precise Windows process layout as well as rejected unrelated Python listeners using mock process records (no real process termination in the test). Existing backend/frontend code is unchanged.

Windows startup and UI smoke tests must still be run locally. Use the single update/test/run PowerShell command and confirm PASS only if the backend and frontend launch successfully.
