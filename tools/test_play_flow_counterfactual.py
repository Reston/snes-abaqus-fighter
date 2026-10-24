"""Keep the current-source comparison patch strictly limited to banner stores."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from play_flow_counterfactual import patched

GAME='before\nimpactBannerCounter=2;\nmiddle\nimpactBannerCounter=2;\nafter\n'
HOOK='    impactBannerCounter=3;impactBannerCombo=0;impactBannerPending=1;impactSettle=1;\n'
DOWN='gameplay stores before\n'+HOOK+'gameplay stores after\n'

class FeedbackReferenceTests(unittest.TestCase):
    def test_exact_patch_preserves_all_other_source(self):
        result=patched(GAME, DOWN)
        self.assertEqual(result, {'src/game.c':GAME.replace('impactBannerCounter=2;', 'impactBannerCounter=0;'),
                                  'src/knockdown.h':'gameplay stores before\ngameplay stores after\n'})
    def test_missing_recovery_classification_rejects(self):
        with self.assertRaises(ValueError):patched(GAME.replace('impactBannerCounter=2;', '', 1), DOWN)
    def test_extra_recovery_classification_rejects(self):
        with self.assertRaises(ValueError):patched(GAME+'impactBannerCounter=2;', DOWN)
    def test_missing_throw_hook_rejects(self):
        with self.assertRaises(ValueError):patched(GAME, DOWN.replace(HOOK,''))
    def test_extra_throw_hook_rejects(self):
        with self.assertRaises(ValueError):patched(GAME, DOWN+HOOK)
    def test_actual_current_source_has_exact_patch_boundary(self):
        root=Path(__file__).resolve().parents[1]
        game=(root/'src/game.c').read_text(encoding='utf-8');down=(root/'src/knockdown.h').read_text(encoding='utf-8')
        result=patched(game,down)
        self.assertEqual(result['src/game.c'], game.replace('impactBannerCounter=2;', 'impactBannerCounter=0;'))
        self.assertEqual(result['src/knockdown.h'], down.replace(HOOK,''))
        self.assertEqual(game.count('impactBannerCounter=2;'),2)
        self.assertEqual(len(game)-len(result['src/game.c']),0)

if __name__=='__main__':unittest.main(verbosity=2)
