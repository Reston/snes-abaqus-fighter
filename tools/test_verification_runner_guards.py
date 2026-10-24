"""Verify command inventory, bounded scheduling and retained failure outcomes."""
from pathlib import Path
import json
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_play_flow_26 import plan,pool,expand,run_job

class VerificationRunnerGuards(unittest.TestCase):
    def test_full_plan_has_each_required_feature_and_native_run_once(self):
        graph=plan();items=[item for group in graph.values() for item in group];ids=[item['id'] for item in items]
        self.assertEqual(len(ids),len(set(ids)))
        required={'native-six','pacing','supers','cpu','feedback','results','training','meter','arenas','arcade','manual','rounds','throw','best','session','normal-guide','confirm','music','motion','repeat','previews','roster','compatibility','launcher','session-limit'}
        self.assertTrue(required<={x['id'] for x in graph['native']})
        self.assertEqual([x['id'] for x in graph['host']],['asset-build','native-publication'])
    def test_stress_shards_cover_all_twelve_fighters_without_overlap(self):
        rows=[x for x in plan()['native'] if x['id'].startswith('stress-')];fighters=[]
        for row in rows:
            a=row['arguments'];begin=a.index('--fighters')+1;end=a.index('--report');fighters.extend(map(int,a[begin:end]))
        self.assertEqual(fighters,list(range(12)))
    def test_merge_inputs_are_the_exact_worker_outputs(self):
        graph=plan();workers={x['id']:x['arguments'][x['arguments'].index('--report')+1] for x in graph['native'] if '--report' in x['arguments']}
        stress=next(x for x in graph['finish'] if x['id']=='merge-stress')['arguments'][2:]
        hours=next(x for x in graph['finish'] if x['id']=='merge-hours')['arguments'][2:]
        self.assertEqual(stress,[workers['stress-'+str(i)] for i in range(4)]);self.assertEqual(hours,[workers['hour-'+str(i)] for i in range(3)])
    def test_argument_expansion_preserves_space_containing_paths(self):
        row=expand({'id':'a','arguments':['--source-ref','<FREEZE>','<RUN>/file.json']},'a'*40,'build/space containing run')
        self.assertEqual(row['arguments'],['--source-ref','a'*40,'build/space containing run/file.json'])
    def test_command_metadata_never_replaces_the_producer_report(self):
        with tempfile.TemporaryDirectory(prefix='verification proof ') as temporary:
            root=Path(temporary);folder=root/'run';folder.mkdir()
            raw=b'{"status":"passed","native_cases":[1,2,3]}\n'
            item={'id':'stress-0','arguments':['-c',"from pathlib import Path; Path('run/stress-0.json').write_bytes("+repr(raw)+")"]}
            result=run_job(root,item,folder,[])
            self.assertEqual(result['exit_code'],0)
            self.assertEqual((folder/'stress-0.json').read_bytes(),raw)
            self.assertEqual(json.loads((folder/'stress-0.command.json').read_bytes()),result)
            self.assertEqual(result['log'],'run/stress-0.log')
    def test_single_worker_stops_before_starting_another_job_after_failure(self):
        started=[];retained=[]
        def execute(item,slot):started.append(item['id']);return {'id':item['id'],'exit_code':1 if item['id']=='bad' else 0}
        with self.assertRaises(RuntimeError):pool([{'id':name} for name in ('bad','unstarted')],1,execute,retained.append)
        self.assertEqual(started,['bad']);self.assertEqual([x['id'] for x in retained],['bad'])
    def test_active_writers_finish_and_their_results_survive_another_failure(self):
        active=threading.Event();started=[];retained=[]
        def execute(item,slot):
            started.append(item['id'])
            if item['id']=='bad':active.wait(2);return {'id':item['id'],'exit_code':1}
            active.set();time.sleep(.05);return {'id':item['id'],'exit_code':0}
        with self.assertRaises(RuntimeError):pool([{'id':name} for name in ('bad','writer','unstarted')],2,execute,retained.append)
        self.assertEqual(set(started),{'bad','writer'});self.assertEqual({x['id'] for x in retained},{'bad','writer'})
    def test_parallelism_is_bounded_and_every_result_is_retained(self):
        lock=threading.Lock();current=0;peak=0;retained=[]
        def execute(item,slot):
            nonlocal current,peak
            with lock:current+=1;peak=max(peak,current)
            time.sleep(.005)
            with lock:current-=1
            return {'id':item['id'],'exit_code':0}
        result=pool([{'id':i} for i in range(8)],2,execute,retained.append)
        self.assertLessEqual(peak,2);self.assertEqual(len(result),8);self.assertEqual({r['id'] for r in retained},set(range(8)))
    def test_worker_exceptions_preserve_the_original_job_identity(self):
        retained=[]
        def execute(item,slot):raise OSError('simulated worker launch failure')
        with self.assertRaises(RuntimeError):pool([{'id':'launch'}],1,execute,retained.append)
        self.assertEqual(retained[0]['id'],'launch');self.assertEqual(retained[0]['exit_code'],-1)
    def test_affinity_failure_is_not_a_false_pass(self):
        with self.assertRaises(RuntimeError):pool([{'id':'a'}],1,lambda item,slot:{'id':'a','exit_code':0,'affinity_error':5},lambda row:None)

if __name__=='__main__':unittest.main(verbosity=2)
