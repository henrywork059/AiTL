"""Real spawned-process lifecycle tests with a synthetic worker, no native dependency."""
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/pc-studio/backend'))
from app.services.sumo_shadow_adapter import ShadowAgent, SumoShadowAdapter
from app.services.sumo_shadow_process import LibsumoSession


def fake_worker(pipe, root, seed):
    try:
        pipe.send(('ok', None))
        tick = 0
        while pipe.recv() == 'step':
            tick += 1
            if seed == 7:
                time.sleep(30)
            pipe.send(('ok', ((ShadowAgent('vehicle', 'v0', tick / 5, 0, 1, 'WC'),), (), ())))
    finally:
        pipe.close()


def failed_start(pipe, root, seed):
    pipe.send(('error', 'missing engine'))
    pipe.close()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('network.xml', 'routes.xml'):
            (self.root / name).write_text('<test/>')
        self.sessions = []
        def factory(seed):
            session = LibsumoSession(self.root, seed, _target=fake_worker)
            self.sessions.append(session)
            return session
        self.adapter = SumoShadowAdapter(factory)
        self.addCleanup(self.adapter.shutdown)

    def test_real_child_reset_and_cleanup(self):
        self.adapter.reset(seed=42)
        a = self.adapter.step(3)
        self.adapter.reset(seed=42)
        self.assertFalse(self.sessions[0].proc.is_alive())
        self.assertEqual(a, self.adapter.step(3))
        self.adapter.shutdown()
        self.assertTrue(all(not s.proc.is_alive() for s in self.sessions))

    def test_forced_loss_clears_snapshot(self):
        self.adapter.reset(seed=42)
        self.sessions[-1].proc.kill()
        self.sessions[-1].proc.join(5)
        with self.assertRaises((OSError, EOFError)):
            self.adapter.step()
        self.assertIsNone(self.adapter.snapshot())
        self.adapter.reset(seed=42)
        self.assertEqual(self.adapter.step().tick, 1)

    def test_timeout_reaps_child(self):
        self.adapter.reset(seed=7)
        session = self.sessions[-1]
        session._timeout = 0.1
        with self.assertRaises(TimeoutError):
            self.adapter.step()
        self.assertFalse(session.proc.is_alive())
        self.assertIsNone(self.adapter.snapshot())

    def test_invalid_fixture_and_start_failure(self):
        with self.assertRaises(RuntimeError):
            LibsumoSession(self.root, 42, _target=failed_start)
        (self.root / 'routes.xml').unlink()
        with self.assertRaises(ValueError):
            LibsumoSession(self.root, 42, _target=fake_worker)


if __name__ == '__main__':
    unittest.main()
