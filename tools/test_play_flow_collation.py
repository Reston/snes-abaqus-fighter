"""Reject incomplete, stale and weakened candidate evidence without emulation."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collate_play_flow_26 import validate_record, feature_coverage

ROM = '1' * 64
SOURCES = {'src/game.c': '2' * 64, 'tools/play.ps1': '3' * 64, 'Test.cmd': '4' * 64}


def record():
    return {'status': 'passed', 'version': '0.26.0', 'rom_sha256': ROM, 'source_sha256': dict(SOURCES),
            'controller_only': True, 'memory_writes': False, 'save_states': False,
            'checks': [{'check': 'observed native assertion', 'passed': True}], 'check_count': 1}


class PlayFlowCollationTests(unittest.TestCase):
    def test_complete_current_record_is_accepted(self):
        self.assertEqual(validate_record(record(), 'example', ROM, SOURCES), 1)

    def test_stale_identity_and_failed_status_are_rejected(self):
        for key, value in (('rom_sha256', '0' * 64), ('version', '0.25.0'), ('status', 'failed')):
            data = record()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_missing_or_modified_command_dependencies_are_rejected(self):
        for key in SOURCES:
            data = record()
            del data['source_sha256'][key]
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_failed_or_empty_assertion_inventory_is_rejected(self):
        for rows in ([], [{'check': 'failed', 'passed': False}]):
            data = record()
            data['checks'] = rows
            with self.subTest(rows=rows), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_zero_or_boolean_execution_counts_cannot_pass(self):
        for executions in (0, -1, True):
            data = record()
            data['checks'][0]['executions'] = executions
            data['check_count'] = executions
            with self.subTest(executions=executions), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_native_failure_arrays_and_failed_checks_are_rejected(self):
        for key, value in (('cadence_failures', [{'frame': 12}]), ('native_failed_checks', [{'passed': False}])):
            data = record()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_memory_write_or_save_state_claims_are_rejected(self):
        for key in ('memory_writes', 'save_states'):
            data = record()
            data[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_record(data, 'example', ROM, SOURCES)

    def test_observed_native_health_cannot_be_omitted(self):
        for health in (None, {'callbacks': 0, 'max_spc_backlog': 0, 'failures': []},
                       {'callbacks': 100, 'max_spc_backlog': 7, 'failures': []}):
            data = {'native_health': health, 'cases': []}
            with self.subTest(health=health), self.assertRaises(RuntimeError):
                feature_coverage('normal-guide', data)

    def test_partial_roster_cannot_become_a_full_guide_proof(self):
        data = {'native_health': {'callbacks': 100, 'max_spc_backlog': 0, 'failures': []},
                'cases': [{'independent': False, 'fighter': 0, 'passed': True, 'native_ground_actions': [1] * 8}]}
        with self.assertRaises(RuntimeError):
            feature_coverage('normal-guide', data)

    def test_arcade_progress_requires_the_eleventh_earned_victory(self):
        data = {'result': {'native_health': {'callbacks': 100, 'max_spc_backlog': 0, 'failures': []},
                          'ladder': [{'shift': s + 1, 'opponent': (s + 5) % 12} for s in range(10)]}}
        with self.assertRaises(RuntimeError):
            feature_coverage('arcade', data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
