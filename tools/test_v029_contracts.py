"""Bounded mutations for the combined preservation policy; no native writes."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v029_contracts as policy


class Contracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root/'assets/generated').mkdir(parents=True)
        self.name = 'assets/generated/fighter00.bin'
        self.prior = {self.name: b'approved-fighter-bytes'}
        (self.root/self.name).write_bytes(self.prior[self.name])

    def generated(self):
        return policy.generated_report(self.root, self.prior, set(), set())

    def test_approved_bytes_are_preserved(self):
        self.assertEqual(self.generated()['preserved_count'], 1)

    def test_rehashed_current_asset_still_rejects_changed_baseline(self):
        current = b'modified-fighter-bytes'
        (self.root/self.name).write_bytes(current)
        forged_row = {'sha256': policy.sha(current), 'preserved': True}
        self.assertTrue(forged_row['preserved'])
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.generated()

    def test_removed_approved_asset_rejected(self):
        (self.root/self.name).unlink()
        with self.assertRaisesRegex(ValueError, 'removed'):
            self.generated()

    def test_unreviewed_added_payload_rejected(self):
        (self.root/'assets/generated/unreviewed.bin').write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.generated()

    def maps(self):
        old = {'fighter': 0x7f0100, 'SECTIONEND_globram.data': 0x7f0598,
               'RAM_USAGE_SLOT_3_BANK_127_END': 1431}
        new = copy.copy(old)
        for name in policy.MARKERS:
            new[name] += sum(policy.STATE.values())
        cursor = old['SECTIONEND_globram.data']
        for name, size in policy.STATE.items():
            new[name] = cursor
            cursor += size
        return old, new

    def test_reserved_arrays_append_without_relocation(self):
        self.assertEqual(policy.ram_report(*self.maps())['reserved_bytes'], 176)

    def test_prior_variable_relocation_rejected(self):
        old, new = self.maps()
        new['fighter'] += 1
        with self.assertRaisesRegex(ValueError, 'address'):
            policy.ram_report(old, new)

    def test_reserved_array_overlap_rejected(self):
        old, new = self.maps()
        new['v29BonusState'] -= 1
        with self.assertRaisesRegex(ValueError, 'overlapped'):
            policy.ram_report(old, new)

    def test_floor_palette_and_real_bitplanes_are_bound(self):
        gfx = bytes([255, 0]*8 + [0]*16)
        tilemap = (2 << 10).to_bytes(2, 'little')*2048
        palette = bytearray(192)
        palette[2:4] = b'\x34\x12'
        pixels = policy.floor_pixels(gfx, tilemap, bytes(palette), 216, width=8)
        self.assertEqual(pixels, b'\x34\x12'*64)
        changed = bytearray(gfx)
        changed[0] = 0
        self.assertNotEqual(pixels, policy.floor_pixels(bytes(changed), tilemap, bytes(palette), 216, width=8))


if __name__ == '__main__':
    unittest.main()
