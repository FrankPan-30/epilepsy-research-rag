"""Loopback HTTP checks using synthetic PDFs; no personal data or downloaded models."""
import json,shutil,sqlite3,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import rag,web_app

def pdf_bytes():
    import pymupdf
    with pymupdf.open() as doc:
        for content in ('Synthetic alarm smoothing threshold evidence for testing. No clinical claims.','Second synthetic page for checking citation navigation.'):
            doc.new_page().insert_text((72,72),content)
        doc.set_metadata({'title':'Synthetic alarm paper','author':'Fixture Author'})
        return doc.tobytes()

def seed_index(app,library='web'):
    data=app.data_dir(library);folder=data/'fixture-v1';folder.mkdir(parents=True,exist_ok=True)
    path=app.workspace/'fixture.pdf';path.write_bytes(pdf_bytes());digest=rag.sha(path)
    paper={'key':'PDF-'+digest,'title':'Synthetic alarm paper','authors':['Fixture Author'],'date':'2024','doi':'','library_source':'pdf_folder','collections':['fixtures']}
    attachment={'key':paper['key'],'path':str(path)}
    citation=rag.citation_for(paper,attachment,1,'fulltext');text='Synthetic alarm smoothing threshold evidence for testing. No clinical claims.'
    with sqlite3.connect(folder/'library.sqlite') as db:
        db.executescript(rag.SCHEMA)
        db.execute('INSERT INTO papers VALUES(?,?,?)',(paper['key'],paper['title'],json.dumps(paper)))
        db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)',(1,paper['key'],paper['key'],1,'Methods','fulltext',text,json.dumps(citation),'text_extracted_unreviewed'))
        db.execute('INSERT INTO search(rowid,title,text) VALUES(?,?,?)',(1,paper['title'],text))
    rag.write_json(folder/'manifest.json',{'papers':1,'pdfs':1,'pages':2,'failed_pdfs':[]})
    rag.write_json(folder/'cards.json',[{'paper_key':paper['key'],'missing_fulltext':False,'fields':{}}])
    rag.write_json(data/'parsed'/(paper['key']+'.json'),{'sha256':digest,'pages':[{'page':n,'text':text,'quality':'text_extracted_unreviewed'} for n in (1,2)]})
    rag.write_json(data/'current.json',{'generation':folder.name})
    return paper['key'],path

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rag-web-test-');self.root=Path(self.temp.name).resolve()
        shutil.copy2(rag.ROOT/'config.example.json',self.root/'config.example.json')
        shutil.copytree(rag.ROOT/'web',self.root/'web')
        self.app=web_app.App(self.root);self.server=web_app.make_server(self.app,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.app.close();self.thread.join();self.temp.cleanup()
    def request(self,path,method='GET',data=None,token=True,headers=None):
        hdr={'X-Local-Token':self.app.token} if token else {}
        hdr.update(headers or {})
        request=Request(self.url+path,data=data,headers=hdr,method=method)
        try:
            with urlopen(request,timeout=10) as response:return response.status,response.read(),response.headers
        except HTTPError as error:return error.code,error.read(),error.headers
    def upload(self,data=None,name='paper.pdf',**kwargs):
        return self.request('/api/upload?'+urlencode({'name':name}),'POST',pdf_bytes() if data is None else data,**kwargs)
    def test_static_page_and_api_session_boundary(self):
        code,body,headers=self.request('/',token=False)
        self.assertEqual(code,200);self.assertIn(b'/app.js',body)
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertNotIn(self.app.token.encode(),body)
        self.assertEqual(self.request('/api/status',token=False)[0],403)
        self.assertEqual(self.request('/api/status')[0],200)
        self.assertEqual(self.request('/config.json')[0],404)
        self.assertEqual(self.request('/web/../../config.json')[0],404)
    def test_origin_and_host_rejection(self):
        self.assertEqual(self.request('/api/status',headers={'Origin':'https://example.com'})[0],403)
        self.assertEqual(self.request('/api/status',headers={'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request('/api/status',headers={'Origin':self.url})[0],200)
        self.assertEqual(self.request('/api/upload','OPTIONS')[0],403)
    def test_upload_validation_size_and_duplicate_identity(self):
        self.assertEqual(self.upload(b'not a pdf')[0],400)
        self.assertEqual(self.upload(name='file.txt')[0],400)
        self.assertEqual(self.upload(b'x',headers={'Content-Length':str(web_app.MAX_UPLOAD+1)})[0],413)
        payload=pdf_bytes()
        code,body,_=self.upload(payload,name='../../outside.pdf')
        self.assertEqual(code,200);self.assertFalse(json.loads(body)['duplicate'])
        code,body,_=self.upload(payload,name='renamed.pdf')
        self.assertEqual(code,200);self.assertTrue(json.loads(body)['duplicate'])
        self.assertEqual(len(list(self.app.uploads.glob('*/*.pdf'))),1)
        self.assertFalse((self.root.parent/'outside.pdf').exists())
        self.assertEqual(list(self.app.workspace.glob('*.upload')),[])
    def test_upload_preserves_existing_config_and_index(self):
        settings=self.root/'config.json';settings.write_text('{"collection_key":"ORIGINAL"}')
        seed_index(self.app,'existing');pointer=self.root/'data/current.json';before=pointer.read_bytes()
        self.assertEqual(self.upload()[0],200)
        self.assertEqual(settings.read_text(),'{"collection_key":"ORIGINAL"}')
        self.assertEqual(pointer.read_bytes(),before)
        status=json.loads(self.request('/api/status')[1])
        self.assertEqual(status['libraries']['existing']['papers'],1)
        self.assertFalse(status['libraries']['web']['available'])
    def test_search_catalog_and_pdf_page_roundtrip(self):
        key,path=seed_index(self.app)
        code,body,_=self.request('/api/search?'+urlencode({'q':'alarm threshold','mode':'keyword','library':'web'}))
        self.assertEqual(code,200);hit=json.loads(body)['results'][0]
        self.assertEqual(hit['citation']['pdf_page'],1)
        self.assertNotIn('zotero_url',hit['citation'])
        self.assertEqual(json.loads(self.request('/api/catalog?library=web')[1])['total'],1)
        query=urlencode({'library':'web','attachment':key,'page':2,'generation':hit['generation']})
        code,body,_=self.request('/api/page?'+query)
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['citation']['pdf_page'],2)
        self.assertEqual(self.request('/api/image?'+query)[1][:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(self.request('/api/pdf?'+query)[1],path.read_bytes())
    def test_reject_stale_generation_unknown_pdf_and_changed_file(self):
        key,path=seed_index(self.app)
        query={'library':'web','attachment':key,'page':1,'generation':'old'}
        self.assertEqual(self.request('/api/page?'+urlencode(query))[0],409)
        query['generation']='fixture-v1';query['attachment']='../../config'
        self.assertEqual(self.request('/api/pdf?'+urlencode(query))[0],400)
        query['attachment']=key;query['page']=0
        self.assertEqual(self.request('/api/page?'+urlencode(query))[0],400)
        query['page']=1;path.write_bytes(path.read_bytes()+b'changed')
        self.assertEqual(self.request('/api/image?'+urlencode(query))[0],409)
    def test_empty_query_and_unbuilt_library_feedback(self):
        self.assertEqual(self.request('/api/search?q=')[0],400)
        self.assertEqual(self.request('/api/search?q=alarm&mode=keyword')[0],409)
        self.assertEqual(self.request('/api/jobs?kind=sync','POST')[0],409)
    def test_localized_errors_preserve_status_codes(self):
        code,body,_=self.request('/api/search?q=',headers={'Accept-Language':'en'})
        self.assertEqual(code,400);self.assertIn('Enter a search query',json.loads(body)['error'])
        code,body,_=self.request('/api/search?q=',headers={'Accept-Language':'zh-CN'})
        self.assertEqual(code,400);self.assertIn('请输入',json.loads(body)['error'])
    def test_background_job_isolated_workspace_and_busy_state(self):
        self.upload();self.app.model_ready=lambda:True
        (self.root/'rag.py').write_text("import os,time\nfrom pathlib import Path\ntime.sleep(.4)\nPath(os.environ['RAG_WORKSPACE'],'job-proof').write_text('isolated')\nprint('done')\n")
        self.assertEqual(self.request('/api/jobs?kind=sync','POST')[0],202)
        self.assertEqual(self.request('/api/jobs?kind=sync','POST')[0],409)
        self.assertEqual(self.upload()[0],409)
        self.app.worker.join(timeout=10)
        self.assertEqual(self.app.status()['job']['status'],'succeeded')
        self.assertTrue((self.app.workspace/'job-proof').exists())
        self.assertFalse((self.root/'job-proof').exists())
    def test_failed_build_keeps_active_snapshot(self):
        seed_index(self.app);self.upload();self.app.model_ready=lambda:True
        pointer=self.app.workspace/'data/current.json';before=pointer.read_bytes()
        (self.root/'rag.py').write_text("raise RuntimeError('synthetic failure')\n")
        self.app.start_job('sync');self.app.worker.join(timeout=10)
        self.assertEqual(self.app.status()['job']['status'],'failed')
        self.assertEqual(pointer.read_bytes(),before)
    def test_isolated_config_uses_source_defaults_without_personal_override(self):
        (self.root/'config.json').write_text('{"collection_key":"PRIVATE"}')
        settings=self.root/'alternate';settings.mkdir();(settings/'config.json').write_text('{"library_source":"pdf_folder","pdf_dir":"/tmp/papers"}')
        cfg=rag.load_config(self.root,settings_root=settings)
        self.assertEqual(cfg['library_source'],'pdf_folder')
        self.assertEqual(cfg['collection_key'],'')

if __name__=='__main__':unittest.main(verbosity=2)
