"""Real upload -> background build -> hybrid search -> page HTTP roundtrip, isolated."""
import json,os,shutil,tempfile,threading,time,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import rag,web_app
from test_web import seed_index

@unittest.skipUnless((rag.MODEL/'local_provenance.json').exists(),'Install the local model for full web integration checks')
class WebPipelineTests(unittest.TestCase):
    def test_real_web_import_build_search_and_citation(self):
        import pymupdf
        with tempfile.TemporaryDirectory(prefix='rag-web-pipeline-') as temp:
            root=Path(temp).resolve()/'文献 workspace';root.mkdir()
            for name in ('rag.py','runtime_support.py','pdf_source.py','config.example.json'):
                shutil.copy2(rag.ROOT/name,root/name)
            shutil.copytree(rag.ROOT/'knowledge',root/'knowledge');shutil.copytree(rag.ROOT/'web',root/'web')
            if os.name=='nt':shutil.copytree(rag.MODEL.parent,root/'models')
            else:(root/'models').symlink_to(rag.MODEL.parent,target_is_directory=True)
            (root/'config.json').write_text('{"collection_key":"UNCHANGED"}',encoding='utf-8')
            app=web_app.App(root);seed_index(app,'existing')
            original=(root/'data/current.json').read_bytes()
            server=web_app.make_server(app,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                def request(path,data=None):
                    with urlopen(Request(f'http://127.0.0.1:{server.server_port}'+path,data=data,headers={'X-Local-Token':app.token}),timeout=60) as response:return response.read()
                with pymupdf.open() as doc:
                    doc.new_page().insert_textbox(pymupdf.Rect(60,60,520,720),'Synthetic alarm protocol. This original software fixture describes smoothing and threshold calibration, alongside a refractory period. It provides enough native text for page extraction and does not contain clinical results or patient data.',fontsize=12)
                    doc.set_metadata({'title':'Synthetic web alarm protocol'})
                    data=doc.tobytes()
                uploaded=json.loads(request('/api/upload?name=synthetic.pdf',data))
                self.assertFalse(uploaded['duplicate'])
                request('/api/jobs?kind=sync',b'')
                deadline=time.monotonic()+180
                while time.monotonic()<deadline:
                    status=json.loads(request('/api/status'))
                    if status['job']['status']!='running':break
                    time.sleep(.2)
                self.assertEqual(status['job']['status'],'succeeded',status['job']['log'])
                self.assertEqual(status['libraries']['web']['papers'],1)
                result=json.loads(request('/api/search?'+urlencode({'library':'web','q':'smoothing threshold','mode':'hybrid'})))
                hit=next(row for row in result['results'] if row['kind']=='fulltext')
                query=urlencode({'library':'web','attachment':hit['attachment_key'],'page':hit['page'],'generation':result['generation']})
                page=json.loads(request('/api/page?'+query))
                self.assertIn('Synthetic alarm protocol',page['text'])
                self.assertNotIn('zotero_url',page['citation'])
                self.assertTrue(request('/api/image?'+query).startswith(b'\x89PNG'))
                self.assertEqual(request('/api/pdf?'+query),data)
                self.assertEqual((root/'config.json').read_text(encoding='utf-8'),'{"collection_key":"UNCHANGED"}')
                self.assertEqual((root/'data/current.json').read_bytes(),original)
            finally:server.shutdown();server.server_close();app.close();thread.join()

if __name__=='__main__':unittest.main(verbosity=2)
