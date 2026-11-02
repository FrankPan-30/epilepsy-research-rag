"""Meaningful checks for corpus provenance, retrieval and persistence boundaries."""
import json, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import rag, experiments
import configure
import demo
import pdf_source

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
            self.assertEqual(cfg['library_source'],'zotero')
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
    def test_mcp_client_configs_preserve_launch_and_environment(self):
        root=Path('/tmp/my research project')
        for client in ('generic','claude-desktop','cursor','vscode'):
            obj=json.loads(json.dumps(configure.mcp_config(root,client)))
            server=obj['servers' if client=='vscode' else 'mcpServers']['epilepsy_research']
            self.assertEqual(server['command'],str(root/'.venv/bin/python'))
            self.assertEqual(server['args'],[str(root/'mcp_server.py')])
            self.assertEqual(server['env']['HF_HUB_OFFLINE'],'1')
            if client in ('vscode','cursor'):self.assertEqual(server['type'],'stdio')
    def test_configure_pdf_folder_and_existing_config_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config.example.json').write_text('{}')
            configure.initialize(root,pdf_dir=root/'My papers')
            cfg=rag.load_config(root)
            self.assertEqual(cfg['library_source'],'pdf_folder')
            self.assertEqual(cfg['pdf_dir'],str((root/'My papers').resolve()))
            before=(root/'config.json').read_bytes()
            with self.assertRaises(FileExistsError):configure.initialize(root)
            self.assertEqual((root/'config.json').read_bytes(),before)
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

class PDFSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def pdf(self,name,title='',author=''):
        import pymupdf
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        with pymupdf.open() as doc:
            doc.new_page().insert_text((72,72),'Synthetic research fixture. No clinical evidence.')
            doc.set_metadata({'title':title,'author':author,'creationDate':'D:20261102000000'})
            doc.save(path)
        return path
    def test_recursive_case_insensitive_import_without_zotero(self):
        self.pdf('nested/one.PDF','Embedded title','Raw PDF author')
        with patch.object(rag,'CFG',{'library_source':'pdf_folder','pdf_dir':str(self.root)}),patch.object(rag,'zotero_inventory',side_effect=AssertionError('Zotero must not be read')):
            paper=rag.inventory()[0]
        self.assertEqual(paper['title'],'Embedded title')
        self.assertEqual(paper['authors'],['Raw PDF author'])
        self.assertEqual(paper['date'],'')  # Creation time is not publication time.
        self.assertEqual(paper['doi'],'')
        self.assertIn('nested',paper['collections'])
    def test_filename_fallback_and_sidecar_provenance(self):
        path=self.pdf('untitled.pdf')
        self.assertEqual(pdf_source.pdf_inventory(self.root)[0]['title'],'untitled')
        path.with_name(path.name+'.json').write_text(json.dumps({'title':'Reviewed title','authors':['A. Author'],'date':'2024','doi':'10.example/fixture','tags':['synthetic']}))
        record=pdf_source.pdf_inventory(self.root)[0]
        self.assertEqual(record['title'],'Reviewed title')
        self.assertEqual(record['date'],'2024')
        self.assertEqual(record['metadata_provenance']['title'],'sidecar')
    def test_duplicate_bytes_and_rename_keep_identity(self):
        first=self.pdf('one.pdf');second=self.root/'sub/two.pdf';second.parent.mkdir();shutil.copy2(first,second)
        rows=pdf_source.pdf_inventory(self.root);self.assertEqual(len(rows),1)
        self.assertEqual(len(rows[0]['duplicate_paths']),1)
        key=rows[0]['key'];first.rename(self.root/'renamed.pdf');second.unlink()
        self.assertEqual(pdf_source.pdf_inventory(self.root)[0]['key'],key)
        self.assertEqual(rag.sha(self.root/'renamed.pdf'),key.removeprefix('PDF-'))
    def test_changed_content_gets_new_identity(self):
        first=self.pdf('one.pdf');old=pdf_source.pdf_inventory(self.root)[0]['key']
        first.unlink();self.pdf('one.pdf','Updated title')
        self.assertNotEqual(pdf_source.pdf_inventory(self.root)[0]['key'],old)
    def test_duplicate_sidecars_merge_and_conflicts_fail(self):
        first=self.pdf('one.pdf');second=self.root/'two.pdf';shutil.copy2(first,second)
        second.with_name(second.name+'.json').write_text('{"date":"2024"}')
        self.assertEqual(pdf_source.pdf_inventory(self.root)[0]['date'],'2024')
        first.with_name(first.name+'.json').write_text('{"date":"2025"}')
        with self.assertRaisesRegex(ValueError,'Conflicting date'):pdf_source.pdf_inventory(self.root)
    def test_invalid_metadata_does_not_silently_drop_fields(self):
        path=self.pdf('one.pdf');sidecar=path.with_name(path.name+'.json')
        for body in ('bad json','[]','{"authors":"Author"}','{"title":5}','{"pdf_path":"/tmp/elsewhere"}'):
            sidecar.write_text(body)
            with self.assertRaises(ValueError):pdf_source.pdf_inventory(self.root)
    def test_missing_empty_hidden_and_symlink_sources(self):
        with self.assertRaises(ValueError):pdf_source.pdf_inventory(self.root/'missing')
        with self.assertRaises(ValueError):pdf_source.pdf_inventory(self.root)
        self.pdf('.hidden/paper.pdf')
        with self.assertRaises(ValueError):pdf_source.pdf_inventory(self.root)
        outside=self.pdf('outside.pdf');folder=self.root/'selected';folder.mkdir()
        (folder/'linked.pdf').symlink_to(outside)
        with self.assertRaises(ValueError):pdf_source.pdf_inventory(folder)
    def test_corrupt_pdf_remains_visible_for_failure_reporting(self):
        (self.root/'broken.pdf').write_text('Not a PDF')
        paper=pdf_source.pdf_inventory(self.root)[0]
        self.assertIn('metadata_error',paper)
        self.assertTrue(paper['attachments'][0]['exists'])
    def test_citations_use_source_specific_links(self):
        self.pdf('空 格.pdf');paper=pdf_source.pdf_inventory(self.root)[0]
        cite=rag.citation_for(paper,paper['attachments'][0],2,'fulltext')
        self.assertNotIn('zotero_url',cite)
        self.assertTrue(cite['file_url'].endswith('#page=2'))
        self.assertNotIn(' ',cite['file_url'])
        zotero={**paper,'key':'ZOTERO01','library_source':'zotero'}
        cite=rag.citation_for(zotero,{'key':'ATTACH01','path':paper['attachments'][0]['path']},2,'fulltext')
        self.assertEqual(cite['zotero_url'],'zotero://open-pdf/library/items/ATTACH01?page=2')
        guidance={**paper,'library_source':'project'}
        self.assertNotIn('zotero_url',rag.citation_for(guidance,{},None,'project_guidance'))

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
