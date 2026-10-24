"""Guard full unmasked comparison and current four-button hour coverage."""
import copy
import gzip
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_play_flow_long_26 import HEAD, RANGES, compare_streams, current_coverage
ROOT=Path(__file__).resolve().parents[1]

def sample(frame,lag=0,key=1,padding=0):
    raw=bytearray(sum(size for _,size in RANGES));raw[31]=padding
    return HEAD.pack(key,0,frame,frame,lag,frame+lag,3,3,0xaaba)+raw

def native_record(mode=2):
    return {'status':'passed','mode':mode,'normal_action_starts':{str(a):int(a!=2) for a in range(1,7)},'stable_fight_lag_increments':0,
            'cadence_failures':[],'native_timing_failures':[],'ambient_failures':[],'spc_fifo_failures':[],'ppu_overflow_frames':[],
            'max_spc_backlog':6,'audio_samples':1000,'audio_peak_sampled':5000,'video_geometry':[256,224],
            'stages':[0,1,2],'live_frames':216356,'core_boots':1,'core_unloads':1,'core_reboots':0,
            'events':{name:3 for name in ('attack','air','throw','guard','special','down','wake','real_contact','damage','arcade_ladder','menu_roster','reset')},
            'training_cpu_live_frames':216356,'rosters':[{'fighter2':i} for i in range(12)]}

class LongSessionGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='long-state-',dir=ROOT/'build');self.path=Path(self.tmp.name).resolve()
        if not self.path.is_relative_to(ROOT/'build'):raise RuntimeError('Fixture cleanup escaped the workspace')
        self.addCleanup(self.tmp.cleanup)
    def files(self,before,after):
        a,b=self.path/'before.gz',self.path/'after.gz';a.write_bytes(gzip.compress(before,mtime=0));b.write_bytes(gzip.compress(after,mtime=0));return a,b
    def test_one_identical_baseline_repeat_retains_every_state_byte(self):
        a,b=self.files(sample(1)+sample(1,1)+sample(2,1,padding=7),sample(1)+sample(2,padding=7)+sample(3))
        result=compare_streams(a,b);self.assertEqual(result['compared_logical_frames'],2);self.assertEqual(result['candidate_collapsed_callbacks'],0)
    def test_a_reserved_padding_byte_is_never_masked(self):
        a,b=self.files(sample(1)+sample(2,padding=7),sample(1)+sample(2,padding=8))
        with self.assertRaises(RuntimeError):compare_streams(a,b)
    def test_controller_input_changes_reject(self):
        a,b=self.files(sample(1)+sample(2),sample(1)+sample(2,key=2))
        with self.assertRaises(RuntimeError):compare_streams(a,b)
    def test_missing_middle_or_tail_publication_rejects(self):
        for after in (sample(1)+sample(3),sample(1)+sample(2)):
            a,b=self.files(sample(1)+sample(2)+sample(3),after)
            with self.subTest(after=len(after)),self.assertRaises(RuntimeError):compare_streams(a,b)
    def test_a_current_candidate_repeat_is_never_collapsed(self):
        a,b=self.files(sample(1)+sample(2),sample(1)+sample(1,1)+sample(2,1))
        with self.assertRaises(RuntimeError):compare_streams(a,b)
    def test_extra_candidate_tail_cannot_hide_differences(self):
        a,b=self.files(sample(1)+sample(2),sample(1)+sample(2)+sample(3))
        with self.assertRaises(RuntimeError):compare_streams(a,b)
    def test_four_real_face_buttons_are_required_and_reserved_action_two_is_not(self):
        result=native_record();self.assertTrue(all(current_coverage(2,result,216356).values()));result['normal_action_starts']['5']=0
        with self.assertRaises(RuntimeError):current_coverage(2,result,216356)
    def test_partial_cpu_roster_or_native_fault_rejects(self):
        for key,value in (('rosters',[{'fighter2':i} for i in range(11)]),('native_timing_failures',[{'lag_delta':1}]),('max_spc_backlog',7),('live_frames',216355)):
            result=native_record();result[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):current_coverage(2,result,216356)

if __name__=='__main__':unittest.main(verbosity=2)
