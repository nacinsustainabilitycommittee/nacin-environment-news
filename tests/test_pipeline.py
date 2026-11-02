import sys, pathlib, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import collector
class PipelineTests(unittest.TestCase):
    def test_filters_irrelevant(self):
        self.assertTrue(collector.relevant('Pangolin scales seized in wildlife trafficking case'))
        self.assertFalse(collector.relevant('Elephants spotted in wildlife sanctuary'))
    def test_url_tracking(self):
        self.assertEqual(collector.normalize_url('https://example.org/case?utm_source=abc&id=3'),'https://example.org/case?id=3')
    def test_reject_bad_scheme(self):
        self.assertIsNone(collector.normalize_url('javascript:alert(1)'))
if __name__=='__main__':unittest.main()
