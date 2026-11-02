"""Real PDF/parser/embedding/MCP integration in a disposable clone; no personal corpus writes."""
import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
import rag

@unittest.skipUnless((rag.MODEL/'local_provenance.json').exists(),'Download the local embedding model for PDF pipeline checks')
class PDFPipelineTests(unittest.TestCase):
    def test_folder_sync_search_updates_and_mcp_without_zotero(self):
        import pymupdf
        with tempfile.TemporaryDirectory(prefix='pdf-rag-integration-') as temp:
            root=Path(temp).resolve()/'文献 clone with spaces';root.mkdir()
            papers=root/'papers';papers.mkdir()
            for name in ('rag.py','runtime_support.py','pdf_source.py','configure.py','config.example.json','mcp_server.py','check_mcp.py'):
                shutil.copy2(rag.ROOT/name,root/name)
            shutil.copytree(rag.ROOT/'knowledge',root/'knowledge')
            if os.name=='nt':shutil.copytree(rag.MODEL.parent,root/'models')
            else:(root/'models').symlink_to(rag.MODEL.parent,target_is_directory=True)
            original=papers/'a paper.pdf'
            with pymupdf.open() as doc:
                for text in (
                    'Synthetic alarm methods. This fictional fixture records smoothing and threshold settings. The refractory period and false alarm count belong to the same evaluation protocol. This text is only for testing retrieval and page citations.',
                    'Synthetic validation methods. LOPOCV holds out a patient in this fictional example. Training, validation and test assignments precede overlapping window extraction. This text is a software fixture and provides no experimental results.'):
                    doc.new_page().insert_textbox(pymupdf.Rect(72,72,520,700),text,fontsize=12)
                doc.set_metadata({'title':'Synthetic alarm protocol fixture','author':'Synthetic Author'})
                doc.save(original)
            sidecar=original.with_name(original.name+'.json');sidecar.write_text('{"date":"2024","tags":["synthetic"]}',encoding='utf-8')
            duplicate=papers/'z duplicate.PDF';shutil.copy2(original,duplicate)
            env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'}
            def run(*args,success=True):
                try:result=subprocess.run([sys.executable,*args],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
                except subprocess.TimeoutExpired as exc:
                    print('Timed out command:',args,file=sys.stderr)
                    for name in ('stdout','stderr'):
                        data=getattr(exc,name) or b''
                        if isinstance(data,bytes):data=data.decode('utf-8',errors='replace')
                        print(name+': '+data[-12000:],file=sys.stderr,flush=True)
                    raise
                if success and result.returncode:self.fail(result.stderr[-8000:])
                if not success:self.assertNotEqual(result.returncode,0)
                return result
            run('configure.py','--pdf-dir',str(papers))
            # No Zotero directory is available in this fixture.
            config=json.loads((root/'config.json').read_text(encoding='utf-8'));config['zotero_data_dir']=str(root/'does-not-exist')
            (root/'config.json').write_text(json.dumps(config),encoding='utf-8')
            inventory=json.loads(run('rag.py','inventory').stdout)
            self.assertEqual(len(inventory),1);key=inventory[0]['key']
            first=json.loads(run('rag.py','sync').stdout)
            self.assertEqual((first['library_source'],first['pdfs'],first['pages'],first['duplicate_pdfs_skipped']),('pdf_folder',1,2,1))
            self.assertEqual(first['failed_pdfs'],[])
            hits=json.loads(run('rag.py','search','alarm smoothing threshold','--paper',key).stdout)['results']
            self.assertTrue(hits)
            full=next(r for r in hits if r['kind']=='fulltext')
            self.assertNotIn('zotero_url',full['citation'])
            self.assertEqual(full['citation']['pdf_page'],1)
            self.assertTrue(full['citation']['file_url'].endswith('#page=1'))
            filtered=json.loads(run('rag.py','search','alarm','--year-min','2024','--collection','papers').stdout)
            self.assertTrue(filtered['results'])
            mcp=json.loads(run('check_mcp.py').stdout)
            self.assertTrue(all(mcp[k] for k in ('workflow_ok','status_ok','search_ok','page_ok','image_ok')))
            parsed=root/'data/parsed'/(key+'.json');mtime=parsed.stat().st_mtime_ns
            repeat=json.loads(run('rag.py','sync').stdout)
            self.assertEqual(repeat['embeddings_reused'],repeat['chunks'])
            self.assertEqual(parsed.stat().st_mtime_ns,mtime)
            additional=papers/'added.pdf'
            with pymupdf.open() as doc:
                doc.new_page().insert_textbox(pymupdf.Rect(72,72,520,700),'Additional synthetic research fixture. This document tests adding and removing a separate file from the selected folder. It has no clinical claims and no patient data.',fontsize=12)
                doc.save(additional)
            added=json.loads(run('rag.py','sync').stdout)
            self.assertEqual(added['papers'],2)
            additional.unlink()
            duplicate.unlink();renamed=papers/'重命名 paper.pdf';original.rename(renamed)
            sidecar.rename(renamed.with_name(renamed.name+'.json'))
            changed=json.loads(run('rag.py','sync').stdout)
            self.assertEqual(changed['duplicate_pdfs_skipped'],0)
            self.assertEqual(changed['papers'],1)
            self.assertEqual(json.loads(run('rag.py','catalog').stdout)['total'],1)
            self.assertEqual(changed['embeddings_reused'],changed['chunks'])
            self.assertEqual(parsed.stat().st_mtime_ns,mtime)
            hits=json.loads(run('rag.py','search','smoothing','--keyword-only').stdout)['results']
            self.assertTrue(any(r['citation'].get('pdf_path')==str(renamed) for r in hits))
            self.assertEqual(json.loads(run('rag.py','inventory').stdout)[0]['key'],key)
            active=(root/'data/current.json').read_bytes();prior_inventory=(root/'data/inventory.json').read_bytes()
            renamed.with_name(renamed.name+'.json').write_text('{"authors":123}',encoding='utf-8')
            run('rag.py','sync',success=False)
            self.assertEqual((root/'data/current.json').read_bytes(),active)
            self.assertEqual((root/'data/inventory.json').read_bytes(),prior_inventory)
            renamed.unlink()
            run('rag.py','sync',success=False)
            self.assertEqual((root/'data/current.json').read_bytes(),active)

if __name__=='__main__':unittest.main(verbosity=2)
