import unittest,sys,pathlib,tempfile
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import import_submission
from collector import read_json
class SubmissionTests(unittest.TestCase):
    def test_import_and_dedupe(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(import_submission,'DATA',pathlib.Path(temp)):
                issue={'number':12,'author':{'login':'test-reader'},'labels':[{'name':'news-submission'}], 'body':'### Article headline\nWildlife seizure report\n\n### Original article URL\nhttps://example.org/report?utm_source=test\n\n### Category\nSeizures & enforcement\n\n### Relevance to Customs officers (optional)\nPublic training context'}
                self.assertTrue(import_submission.import_issue(issue))
                self.assertFalse(import_submission.import_issue(issue))
                q=read_json(pathlib.Path(temp)/'pending.json',[])
                self.assertEqual(len(q),1)
                self.assertEqual(q[0]['url'],'https://example.org/report')
                self.assertEqual(q[0]['status'],'pending')
    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            import_submission.import_issue({'labels':['news-submission'],'body':'### Article headline\nX\n### Original article URL\njavascript:alert(1)\n### Category\nWildlife trafficking'})
if __name__=='__main__':unittest.main()
