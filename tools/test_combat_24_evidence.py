"""Reject current timing failures even when an envelope labels them historical."""
import copy
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import collate_combat_24 as gate

ROM='a'*64


def producer(path):
    return gate.sha(gate.canonical(path,(gate.ROOT/path).read_bytes()))


def native(engine,rows,path):
    return {'status':'passed','rom_sha256':ROM,'engine':engine,
            'producer_sha256':producer(path),
            'host':{'gui_opened':False,'audio_device_opened':False},'cases':rows}


def fixture():
    names=('fighter','stage','phase','approach_port','spacing')
    identities=list(itertools.product(range(12),range(3),range(3),range(2),('wide','close')))
    cases=[dict(zip(names,key),status='passed',failures=[],sdk_lag_increments=0,callbacks=10)
           for key in identities]
    compared=[dict(zip(names,key),status='passed',issues=[],differences=[],logical_ticks=10,
                   ordered_complete_frame_sets_equal=True,candidate_collapsed_callbacks=0)
              for key in identities]
    cpus=[{'fighter':f,'difficulty':d,'status':'passed','failures':[],
           'sdk_lag_increments':0,'callbacks':10,
           'comparison':{'status':'passed','differences':[],'logical_ticks':10}}
          for f,d in itertools.product(range(12),range(3))]
    return {'status':'passed','version':'0.24.0','rom_sha256':ROM,
            'candidate_native':native('snes9x',cases,'tools/test_special_24_timing.py'),
            'comparison':{'status':'passed','rom_sha256':ROM,
                'producer_sha256':producer('tools/compare_special_24_state.py'),
                'normalization':False,'fighter_bytes':128,'wave_bytes':32,
                'whole_state_fields':['fighters_hex','waves_hex','recoil','supers_hex'],
                'candidate_collapsed_callbacks':0,'issues':[],'case_count':432,
                'logical_ticks':4320,'cases':compared,
                'historical_baseline_diagnostics':{'status':'failed','straddles':12}},
            'cpu_snes9x':native('snes9x',cpus,'tools/test_special_24_cpu_timing.py'),
            'cpu_accuracy':native('accuracy',[copy.deepcopy(c) for c in cpus if c['difficulty']==2],
                                  'tools/test_special_24_cpu_timing.py')}


class TimingEvidenceGuards(unittest.TestCase):
    def setUp(self):self.report=fixture()
    def validate(self):gate.validate_timing(self.report,'0.24.0',ROM)
    def test_historical_failures_do_not_hide_current_passes(self):self.validate()
    def test_failed_current_case_cannot_be_relabelled_historical(self):
        for key,value in (('status','failed'),('sdk_lag_increments',1),
                          ('failures',[{'kind':'Historical baseline','sdk_lag':1}])):
            with self.subTest(key=key):
                report=copy.deepcopy(self.report);report['candidate_native']['cases'][0][key]=value
                with self.assertRaisesRegex(RuntimeError,'Current timing case failed'):
                    gate.validate_timing(report,'0.24.0',ROM)
    def test_duplicate_case_inventory_rejected(self):
        cases=self.report['candidate_native']['cases'];cases[-1]=copy.deepcopy(cases[0])
        with self.assertRaisesRegex(RuntimeError,'inventory differs'):self.validate()
    def test_unmasked_state_difference_rejected(self):
        self.report['comparison']['cases'][0]['differences']=[{'fighters_hex':['00','01']}]
        with self.assertRaisesRegex(RuntimeError,'whole-state comparison failed'):self.validate()
    def test_candidate_collapse_rejected(self):
        self.report['comparison']['candidate_collapsed_callbacks']=1
        with self.assertRaisesRegex(RuntimeError,'contract differs'):self.validate()
    def test_partial_cpu_roster_rejected(self):
        self.report['cpu_accuracy']['cases'].pop()
        with self.assertRaisesRegex(RuntimeError,'inventory differs'):self.validate()


if __name__=='__main__':unittest.main()
