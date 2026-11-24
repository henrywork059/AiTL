"""Offline discovery and process execution do not need a server or hardware."""
from pathlib import Path
from tempfile import TemporaryDirectory

from run_offline_tests import discover_tests, run_tests


def main() -> int:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        scripts = root / "scripts"
        scripts.mkdir()
        for name in ("test_z.py", "test_a.py", "test_update_test_run_script.py"):
            (scripts / name).write_text(
                f"from pathlib import Path\nwith Path('trace.txt').open('a') as f: f.write({name!r} + '\\n')\n",
                encoding="utf-8",
            )
        for name in ("test_backend_smoke.py", "test_camera_transport_benchmark.py",
                     "test_camera_transport_isolation.py"):
            (scripts / name).write_text("raise AssertionError('must not run')\n", encoding="utf-8")
        assert discover_tests(scripts) == ["test_a.py", "test_update_test_run_script.py", "test_z.py"]
        assert discover_tests(scripts, skip_preflight=True) == ["test_a.py", "test_z.py"]
        assert run_tests(scripts, skip_preflight=True) == 0
        trace = root / "trace.txt"
        assert trace.read_text().splitlines() == ["test_a.py", "test_z.py"]
        trace.unlink()
        assert run_tests(scripts, focused=[], skip_preflight=True) == 0 and not trace.exists()
        assert run_tests(scripts, focused=["test_z.py"], skip_preflight=True) == 0
        assert trace.read_text().splitlines() == ["test_z.py"]
        try:
            run_tests(scripts, focused=["test_backend_smoke.py"])
        except ValueError:
            pass
        else:
            raise AssertionError("excluded test accepted")
        trace.unlink()
        (scripts / "test_a.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        assert run_tests(scripts, skip_preflight=True) == 7 and not trace.exists()
    print("[PASS] deterministic discovery, exclusions, focused selection and fail-fast execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
