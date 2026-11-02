"""Meaningful checks for corpus provenance, retrieval and persistence boundaries."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import rag, experiments
import configure
import demo

class UnitTests(unittest.TestCase):
    def test_synthetic_demo_isolated_from_personal_corpus(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rag,'DATA',Path(folder)):
            result=demo.run_demo()
            self.assertEqual(result['results'][0]['paper_key'],'DEMO-ALARM')
            self.assertEqual(result['mode'],'keyword')
            self.assertTrue(all(r['kind']=='synthetic_demo' and r['citation']['pdf_page'] is None for r in result['results']))
            self.assertEqual(list(Path(folder).iterdir()),[])
    def test_synthetic_demo_protocol_and_missing_evidence(self):
        self.assertEqual(demo.run_demo('LOPOCV validation')['results'][0]['paper_key'],'DEMO-SPLIT')
        self.assertEqual(demo.run_demo('zzzzunmatchedtoken')['results'],[])
    def test_config_defaults_and_local_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'config.example.json').write_text(json.dumps({'zotero_data_dir':'~/Zotero','collection_name':'default','collection_key':''}))
            self.assertEqual(rag.load_config(root)['collection_name'],'default')
            (root/'config.json').write_text(json.dumps({'collection_key':'LOCAL123'}))
            cfg=rag.load_config(root)
            self.assertEqual(cfg['collection_key'],'LOCAL123')
            self.assertTrue(Path(cfg['zotero_data_dir']).is_absolute())
    def test_configure_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'config.example.json').write_text('{}')
            configure.initialize(root,'~/Zotero','my collection','KEY12345')
            before=(root/'config.json').read_text()
            with self.assertRaises(FileExistsError):configure.initialize(root,'/tmp','other')
            self.assertEqual((root/'config.json').read_text(),before)
    def test_mcp_command_handles_spaces_in_clone_path(self):
        import shlex
        path=Path('/tmp/my research project')
        args=shlex.split(configure.mcp_command(path))
        self.assertEqual(args[-2:], [str(path/'.venv/bin/python'),str(path/'mcp_server.py')])
    def test_pdf_geometry_preserves_coordinates(self):
        import pymupdf
        self.assertEqual(json.loads(rag.dumps({'bbox':pymupdf.Rect(1,2,3,4)}))['bbox'],[1,2,3,4])
    def test_experiment_states_and_paths(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(experiments,'DATA',Path(folder)):
            rec={**experiments.TEMPLATE,'id':'unit-test','question':'q','hypothesis':'h','split_protocol':'LOPOCV'}
            experiments.save(rec)
            with self.assertRaises(ValueError):experiments.save({**rec,'id':'../escape'})
            with self.assertRaises(ValueError):experiments.save({**rec,'status':'completed'})
            self.assertEqual(json.loads((Path(folder)/'experiments/unit-test/current.json').read_text())['status'],'planned')

@unittest.skipUnless((rag.DATA/'current.json').exists(),'No local corpus; build with rag.py sync for corpus checks')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.lib=rag.Library()
    def test_pdf_coverage_and_no_failures(self):
        status=self.lib.status()
        inventory=json.loads((rag.DATA/'inventory.json').read_text())
        self.assertEqual(status['papers'],len(inventory))
        self.assertEqual(status['pdfs'],sum(a['exists'] for p in inventory for a in p['attachments']))
        self.assertEqual(status['failed_pdfs'],[])
    def test_vectors_match_index(self):
        import numpy as np
        v=np.load(self.lib.folder/'vectors.npy')
        self.assertEqual(len(v),self.lib.db.execute('SELECT count(*) FROM chunks').fetchone()[0])
        self.assertTrue(np.isfinite(v).all())
        self.assertTrue(np.allclose(np.linalg.norm(v,axis=1),1,atol=1e-4))
    def test_pages_and_file_provenance(self):
        for r in self.lib.db.execute("SELECT * FROM chunks WHERE kind IN ('fulltext','references')"):
            cite=json.loads(r['citation'])
            self.assertTrue(Path(cite['pdf_path']).is_file())
            parsed=json.loads((rag.DATA/'parsed'/(r['attachment_key']+'.json')).read_text())
            self.assertGreaterEqual(r['page'],1);self.assertLessEqual(r['page'],len(parsed['pages']))
            # Chunk body comes from the corresponding extracted page, barring heading normalization.
            text=parsed['pages'][r['page']-1]['text']
            self.assertIn(r['text'].strip(),text)
    def test_no_embedding_truncation(self):
        tokenizer=rag.model().tokenizer
        for r in self.lib.db.execute('SELECT c.text,p.title FROM chunks c JOIN papers p ON p.key=c.paper_key'):
            title=tokenizer.decode(tokenizer.encode(r['title'],add_special_tokens=False)[:45])
            tokens=tokenizer.encode('passage: '+title+'\n'+r['text'],add_special_tokens=True)
            self.assertLessEqual(len(tokens),512)
    def test_keyword_source_isolation(self):
        a=self.lib.search('LOPOCV',source='project',mode='keyword')
        self.assertTrue(a['results'])
        self.assertTrue(all(r['kind']=='project_guidance' for r in a['results']))
        b=self.lib.search('seizure prediction',source='papers',mode='keyword')
        self.assertTrue(all(r['kind'] in ['metadata','fulltext','ocr','layout_text'] for r in b['results']))
    def test_reject_unknown_attachment_and_page(self):
        with self.assertRaises(ValueError):self.lib.page('../../anything',1)
        row=self.lib.db.execute('SELECT attachment_key FROM chunks WHERE attachment_key IS NOT NULL LIMIT 1').fetchone()
        with self.assertRaises(ValueError):self.lib.page(row[0],0)
    def test_exact_title_retrievable(self):
        q='EEG epilepsy seizure prediction the post-processing stage as a chronology'
        out=self.lib.search(q,limit=8)
        self.assertIn('QRUMQNXJ',[r['paper_key'] for r in out['results']])
    def test_dense_scores_without_runtime_warnings(self):
        import math,warnings
        with warnings.catch_warnings():
            warnings.simplefilter('error',RuntimeWarning)
            out=self.lib.search('false alarm smoothing threshold',limit=8)
        self.assertTrue(out['results'])
        scores=[r['semantic_score'] for r in out['results'] if r['semantic_score'] is not None]
        self.assertTrue(scores)
        self.assertTrue(all(math.isfinite(s) and -1.00001<=s<=1.00001 for s in scores))
    def test_catalog_includes_unknown_fields(self):
        out=self.lib.catalog(field='history_information')
        self.assertEqual(sum(not p['key'].startswith('LOCAL:') for p in out['papers']),self.lib.status()['papers'])
        self.assertTrue(any(p['candidate_evidence_count']==0 for p in out['papers']))
    def test_collection_filter_and_empty_selection(self):
        r=self.lib.search('seizure prediction',collection='历史信息',mode='keyword')
        self.assertTrue(r['results'])
        for x in r['results']:
            self.assertIn('历史信息',self.lib.paper(x['paper_key'])['metadata']['collections'])
        self.assertEqual(self.lib.search('seizure',collection='nonexistent-collection',mode='keyword')['results'],[])

if __name__=='__main__':unittest.main(verbosity=2)
