"""Failure-report lifecycle tests using synthetic hosts, without loading an emulator."""
from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_endurance as endurance


class FakeHost:
    instances = []

    def __init__(self, **keywords):
        self.frames = 1
        self.boot_count = 1
        self.unload_count = 0
        self.close_calls = 0
        self.instances.append(self)

    def state(self):
        return {'screen': 3, 'native_screen': 3, 'paused': 0}

    def close(self):
        self.close_calls += 1
        self.unload_count += 1


class FakeRun:
    error = None

    def __init__(self, *arguments):
        self.total_frames = 0
        self.live_frames = 0
        self.training_cpu_live_frames = 0
        self.rosters = []
        self.stages = set()
        self.events = {}
        self.previous = None
        self.cadence_failures = [{'fixture': 'cadence', 'at': 1}]
        self.native_timing_failures = [{'fixture': 'native timing', 'at': 1}]
        self.ambient_failures = []
        self.spc_fifo_failures = []
        self.overflow_frames = []
        self.failure_states = [{'fixture': 'read-only state', 'at': 1}]

    def result(self, host, elapsed):
        if self.error is not None:
            raise self.error
        # This deliberately incomplete synthetic record cannot pass any
        # native release gate. Here it exercises only the successful exit.
        return {'status': 'passed', 'synthetic_fixture': True}


class EnduranceReporting(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=endurance.ROOT/'build')
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, (endurance.ROOT/'build').resolve())
        self.addCleanup(self.temporary.cleanup)
        self.path = self.directory/'mode2.json'
        self.original = b'{"status":"passed","rom_sha256":"historical fixture"}\n'
        self.path.write_bytes(self.original)
        FakeHost.instances.clear()
        FakeRun.error = None

    def run_fixture(self, *, error=None, boot_error=None):
        FakeRun.error = error

        def advance(host, runner, *arguments):
            runner.total_frames += 1
            return host.state()

        with ExitStack() as stack:
            for name, value in (
                ('LongRunHost', FakeHost), ('EnduranceRun', FakeRun),
                ('rom_identity', lambda: ('f'*64, 4194304)),
                ('core_identity', lambda: {'synthetic_fixture': True}),
                ('MODE_REPORT', self.directory/'mode{mode}.json'),
                ('assert_loaded_state', lambda *args: None),
                ('select_training_cpu', lambda host, runner: host.state()),
                ('keys_for', lambda *args: ([], [])), ('tracked_step', advance),
            ):
                stack.enter_context(patch.object(endurance, name, value))
            stack.enter_context(patch.object(endurance, 'boot', side_effect=boot_error))
            return endurance.run_mode(2, 1, benchmark=True, coverage_required=False)

    def test_failure_replaces_old_pass_keeps_diagnostics_and_original_error(self):
        error = AssertionError('synthetic cadence failure')
        with self.assertRaises(AssertionError) as caught:
            self.run_fixture(error=error)
        self.assertIs(caught.exception, error)
        record = json.loads(self.path.read_bytes())
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['rom_sha256'], 'f'*64)
        self.assertEqual(record['error'], repr(error))
        self.assertEqual(record['cadence_failures'], [{'fixture': 'cadence', 'at': 1}])
        self.assertEqual(record['native_timing_failures'], [{'fixture': 'native timing', 'at': 1}])
        self.assertEqual(record['failure_states'], [{'fixture': 'read-only state', 'at': 1}])
        self.assertEqual(record['core_boots'], 1)
        self.assertEqual(record['core_unloads'], 1)
        self.assertEqual(record['core_reboots'], 0)
        self.assertEqual(FakeHost.instances[0].close_calls, 1)

    def test_boot_failure_is_recorded_and_the_open_host_is_closed(self):
        error = RuntimeError('synthetic boot failure')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(boot_error=error)
        self.assertIs(caught.exception, error)
        record = json.loads(self.path.read_bytes())
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['frames'], 0)
        self.assertEqual(record['core_unloads'], 1)
        self.assertEqual(FakeHost.instances[0].close_calls, 1)

    def test_success_returns_to_the_existing_caller_without_writing_a_failure(self):
        record = self.run_fixture()
        self.assertIs(record['synthetic_fixture'], True)
        self.assertEqual(record['status'], 'passed')
        self.assertEqual(record['core_unloads'], 1)
        self.assertEqual(FakeHost.instances[0].close_calls, 1)
        self.assertEqual(self.path.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
