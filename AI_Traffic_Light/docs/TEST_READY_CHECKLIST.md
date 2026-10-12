# V0322 Test-Ready Checklist

```text
version: 0_3_22
previous_version: 0_3_21
passed_baseline: 0_3_11
status: Windows fresh-install dependency fix candidate
```

- [ ] A new Windows backend virtual environment installs pinned `httpx==0.28.1` from `requirements.txt`.
- [ ] `python scripts/test_camera_simulation_api.py` imports FastAPI TestClient and passes.
- [ ] Unchanged camera, simulation, crosswalk and other tests pass.
- [ ] `python scripts/check_structure.py` and frontend typecheck/build pass.
- [ ] The complete Windows update/test/run workflow reaches backend health/smoke and opens PC Studio.
- [ ] Owner confirms PASS; `0_3_11` remains baseline until then.
