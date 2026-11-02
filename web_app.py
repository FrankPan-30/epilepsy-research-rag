"""Single-user loopback UI. Uploads use a separate workspace; no hosted service."""
import argparse,contextlib,hashlib,json,os,re,secrets,subprocess,sys,tempfile,threading,webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path,PureWindowsPath
from runtime_support import child_process_options,stop_process_tree
from urllib.parse import parse_qs,urlsplit,quote
import rag

MAX_UPLOAD=100*1024*1024
ERROR_EN={
    '请选择有效的文库。':'Choose a valid library.',
    '这个文库还没有索引。请先导入 PDF 并点击“建立 / 更新索引”。':'This library has no index yet. Import PDFs, then choose Build / update index.',
    '文库已更新，请重新检索后查看引用。':'The library has changed. Search again before opening a citation.',
    '正在处理文库，请等待当前任务完成。':'A library task is running. Wait for it to finish.',
    '请选择小于或等于 100 MB 的 PDF。':'Choose a PDF no larger than 100 MB.',
    '只支持 PDF 文件。':'Only PDF files are supported.',
    '文件上传中断，请重试。':'The upload was interrupted. Please try again.',
    '无法读取这个 PDF；请确认文件有效且没有密码保护。':'Cannot read this PDF. Check that it is valid and not password-protected.',
    '已有任务在运行，请稍候。':'A task is already running. Please wait.',
    '未知任务。':'Unknown task.',
    '请先下载免费的本地检索模型。':'Download the free local retrieval model first.',
    '请先选择 PDF 文件或文件夹。':'Choose PDF files or a folder first.',
    '引用缺少索引版本，请重新检索。':'This citation has no index version. Search again.',
    'PDF 已变更，请先更新索引再查看原文。':'The PDF has changed. Update the index before viewing its pages.',
    '访问会话已失效，请用启动窗口中的链接重新打开。':'This session has expired. Reopen the full link in the launcher window.',
    '请输入 1–1000 个字符的检索问题。':'Enter a search query between 1 and 1000 characters.',
    '模型尚未就绪，请下载模型或使用关键词检索。':'The model is not ready. Download it or choose keyword-only search.',
    '本地处理失败，请检查安装环境或运行详情。':'Local processing failed. Check your installation or the run details.',
}

class WebError(Exception):
    def __init__(self,message,status=400):super().__init__(message);self.status=status

class App:
    def __init__(self,root=rag.ROOT):
        self.root=Path(root).resolve();self.workspace=self.root/'data/web'
        self.uploads=self.workspace/'uploads';self.uploads.mkdir(parents=True,exist_ok=True)
        config={**rag.load_config(self.root),'library_source':'pdf_folder','pdf_dir':str(self.uploads)}
        try:
            with (self.workspace/'config.json').open('x',encoding='utf-8') as file:json.dump(config,file,ensure_ascii=False,indent=2)
        except FileExistsError:pass
        self.token=secrets.token_urlsafe(32)
        self.lock=threading.RLock();self.query_lock=threading.RLock()
        self.job={'status':'idle','kind':None,'message':'','log':[]}
        self.process=None;self.worker=None;self.closing=False
    def data_dir(self,library):
        if library=='web':return self.workspace/'data'
        if library=='existing':return self.root/'data'
        raise WebError('请选择有效的文库。')
    def model_ready(self):
        model=self.root/'models/multilingual-e5-small'
        return all((model/name).is_file() for name in ('local_provenance.json','model.safetensors','tokenizer.json'))
    @contextlib.contextmanager
    def library(self,name,generation=None):
        with self.query_lock:
            data=self.data_dir(name)
            if not (data/'current.json').exists():raise WebError('这个文库还没有索引。请先导入 PDF 并点击“建立 / 更新索引”。',409)
            lib=rag.Library(data_dir=data)
            try:
                if generation and lib.folder.name!=generation:raise WebError('文库已更新，请重新检索后查看引用。',409)
                yield lib
            finally:lib.db.close()
    def status(self):
        libraries={}
        for name in ('web','existing'):
            available=(self.data_dir(name)/'current.json').exists()
            row={'available':available,'papers':0,'pdfs':0,'pages':0,'failed_pdfs':0}
            if available:
                with self.library(name) as lib:
                    manifest=lib.status()
                    row.update({k:manifest.get(k,0) for k in ('papers','pdfs','pages')})
                    row.update(generation=lib.folder.name,updated=manifest.get('completed_at',''),failed_pdfs=len(manifest.get('failed_pdfs',[])))
            libraries[name]=row
        with self.lock:job={**self.job,'log':list(self.job['log'])}
        return {'libraries':libraries,'uploads':len(list(self.uploads.glob('*/*.pdf'))),'model_ready':self.model_ready(),'job':job,'max_upload_mb':MAX_UPLOAD//1024//1024}
    def import_pdf(self,name,stream,length):
        with self.lock:
            if self.job['status']=='running':raise WebError('正在处理文库，请等待当前任务完成。',409)
            if not 0<length<=MAX_UPLOAD:raise WebError('请选择小于或等于 100 MB 的 PDF。',413)
            name=Path(name.replace('\\','/')).name
            if not name.lower().endswith('.pdf'):raise WebError('只支持 PDF 文件。')
            stem=re.sub(r'[\x00-\x1f<>:"|?*]','_',Path(name).stem).strip(' .') or 'paper'
            stem=stem.encode('utf-8')[:80].decode('utf-8',errors='ignore')
            safe=stem+'.pdf'
            if PureWindowsPath(safe).is_reserved():safe='_'+safe
            with tempfile.NamedTemporaryFile(dir=self.workspace,suffix='.upload',delete_on_close=False) as tmp:
                digest=hashlib.sha256();remaining=length
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:raise WebError('文件上传中断，请重试。')
                    remaining-=len(block);tmp.write(block);digest.update(block)
                tmp.flush()
                import pymupdf
                try:
                    with pymupdf.open(tmp.name) as document:
                        if not document.is_pdf or document.needs_pass or len(document)==0:raise ValueError('Unsupported PDF')
                        pages=len(document)
                except Exception as exc:raise WebError('无法读取这个 PDF；请确认文件有效且没有密码保护。') from exc
                key=digest.hexdigest();folder=self.uploads/key
                if folder.exists():return {'name':name,'duplicate':True,'pages':pages}
                folder.mkdir()
                try:
                    # Keep the original basename for metadata fallback; duplicate bytes share a directory.
                    with (folder/safe).open('xb') as dest:
                        tmp.seek(0)
                        while block:=tmp.read(1024*1024):dest.write(block)
                except Exception:
                    (folder/safe).unlink(missing_ok=True);folder.rmdir();raise
                return {'name':name,'duplicate':False,'pages':pages}
    def start_job(self,kind):
        with self.lock:
            if self.job['status']=='running':raise WebError('已有任务在运行，请稍候。',409)
            if kind not in ('sync','model'):raise WebError('未知任务。')
            if kind=='sync':
                if not self.model_ready():raise WebError('请先下载免费的本地检索模型。',409)
                if not any(self.uploads.glob('*/*.pdf')):raise WebError('请先选择 PDF 文件或文件夹。',409)
            if kind=='model' and self.model_ready():return {'status':'succeeded','message':'本地模型已就绪。'}
            self.job={'status':'running','kind':kind,'message':'正在建立索引…' if kind=='sync' else '正在下载本地检索模型…','log':[]}
            self.worker=threading.Thread(target=self._run_job,args=(kind,),daemon=True);self.worker.start()
            return dict(self.job)
    def _run_job(self,kind):
        env={**os.environ,'RAG_WORKSPACE':str(self.workspace),'PYTHONUNBUFFERED':'1','PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','HF_HUB_DISABLE_TELEMETRY':'1'}
        if kind=='sync':env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        else:
            env.pop('HF_HUB_OFFLINE',None);env.pop('TRANSFORMERS_OFFLINE',None)
        args=[sys.executable,str(self.root/('rag.py' if kind=='sync' else 'download_model.py'))]
        if kind=='sync':args.append('sync')
        try:
            with (self.workspace/'last-job.log').open('w',encoding='utf-8') as log:
                with self.lock:
                    if self.closing:raise RuntimeError('应用已停止。')
                    process=subprocess.Popen(args,cwd=self.root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**child_process_options())
                    self.process=process
                for line in process.stdout:
                    log.write(line);log.flush()
                    with self.lock:
                        self.job['log']=(self.job['log']+[line.rstrip()[-1000:]])[-30:]
                        if re.match(r'^PDF \d+/\d+',line):self.job['message']='解析文献：'+line.split(':',1)[0].removeprefix('PDF ')
                        elif line.startswith('Embedding '):self.job['message']='正在生成本地检索向量…'
                process.stdout.close()
                code=process.wait()
                if code:raise RuntimeError('处理失败，请展开运行详情查看原因。已有索引仍可使用。')
            with self.lock:self.job.update(status='succeeded',message='索引已更新，可以开始检索。' if kind=='sync' else '模型已就绪，可以建立索引。')
        except Exception as exc:
            with self.lock:self.job.update(status='failed',message=str(exc))
        finally:
            with self.lock:self.process=None
    def close(self):
        with self.lock:self.closing=True;process=self.process
        if process:stop_process_tree(process)
        if self.worker:self.worker.join(timeout=12)
    def page(self,library,attachment,page,generation):
        if not generation:raise WebError('引用缺少索引版本，请重新检索。',409)
        with self.library(library,generation) as lib:
            result=lib.page(attachment,page)
            parsed=json.loads((lib.data/'parsed'/(attachment+'.json')).read_text(encoding='utf-8'))
            path=Path(result['citation']['pdf_path'])
            if rag.sha(path)!=parsed['sha256']:raise WebError('PDF 已变更，请先更新索引再查看原文。',409)
            return result,path,len(parsed['pages'])

class Handler(BaseHTTPRequestHandler):
    server_version='ResearchLibrary/0.4'
    def setup(self):super().setup();self.connection.settimeout(30)
    def log_message(self,*args):pass  # Do not log private queries, filenames or launch tokens.
    def error_text(self,message):return ERROR_EN.get(message,message) if self.headers.get('Accept-Language','zh').lower().startswith('en') else message
    def reply(self,status,body,content_type='application/json; charset=utf-8',headers=None):
        if isinstance(body,(dict,list)):body=json.dumps(body,ensure_ascii=False).encode()
        elif isinstance(body,str):body=body.encode()
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key,value in (headers or {}).items():self.send_header(key,value)
        self.end_headers();self.wfile.write(body)
    def guard(self,api):
        host=self.headers.get('Host','');port=self.server.server_port
        if host not in (f'127.0.0.1:{port}',f'localhost:{port}'):raise WebError('Invalid local host.',403)
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'):raise WebError('Cross-origin requests are not allowed.',403)
        if api and not secrets.compare_digest(self.headers.get('X-Local-Token',''),self.server.app.token):
            raise WebError('访问会话已失效，请用启动窗口中的链接重新打开。',403)
    def dispatch(self):
        try:
            route=urlsplit(self.path);query={k:v[0] for k,v in parse_qs(route.query).items()}
            self.guard(route.path.startswith('/api/'))
            if self.command=='GET' and route.path in ('/','/app.js','/style.css'):
                name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[route.path]
                mime={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[name]
                return self.reply(200,(self.server.app.root/'web'/name).read_bytes(),mime)
            if not route.path.startswith('/api/'):raise WebError('Not found.',404)
            app=self.server.app;library=query.get('library','web')
            if self.command=='POST':
                if route.path=='/api/upload':
                    if self.headers.get('Transfer-Encoding'):raise WebError('Chunked uploads are not supported.',400)
                    return self.reply(200,app.import_pdf(query.get('name',''),self.rfile,int(self.headers.get('Content-Length','0'))))
                if route.path=='/api/jobs':return self.reply(202,app.start_job(query.get('kind','')))
                raise WebError('Not found.',404)
            if self.command!='GET':raise WebError('Method not allowed.',405)
            if route.path=='/api/status':return self.reply(200,app.status())
            if route.path=='/api/search':
                q=query.get('q','').strip()
                if not q or len(q)>1000:raise WebError('请输入 1–1000 个字符的检索问题。')
                mode=query.get('mode','hybrid')
                if mode=='hybrid' and not app.model_ready():raise WebError('模型尚未就绪，请下载模型或使用关键词检索。',409)
                with app.library(library) as lib:result=lib.search(q,limit=8,mode=mode)
                return self.reply(200,result)
            if route.path=='/api/catalog':
                with app.library(library) as lib:result=lib.catalog(query.get('q',''))
                return self.reply(200,result)
            if route.path in ('/api/page','/api/image','/api/pdf'):
                page=int(query.get('page','1'))
                result,path,pages=app.page(library,query.get('attachment',''),page,query.get('generation'))
                if route.path=='/api/page':return self.reply(200,{'citation':result['citation'],'text':result['page']['text'],'quality':result['page']['quality'],'page':page,'pages':pages})
                if route.path=='/api/pdf':return self.reply(200,path.read_bytes(),'application/pdf',{'Content-Disposition':"attachment; filename*=UTF-8''"+quote(path.name)})
                import pymupdf
                with pymupdf.open(path) as doc:
                    p=doc[page-1];scale=min(1.5,2200/max(p.rect.width,p.rect.height))
                    png=p.get_pixmap(matrix=pymupdf.Matrix(scale,scale)).tobytes('png')
                return self.reply(200,png,'image/png')
            raise WebError('Not found.',404)
        except WebError as exc:self.reply(exc.status,{'error':self.error_text(str(exc))})
        except (ValueError,KeyError,FileNotFoundError) as exc:self.reply(400,{'error':str(exc)})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:self.reply(500,{'error':self.error_text('本地处理失败，请检查安装环境或运行详情。')})
    do_GET=dispatch
    do_POST=dispatch
    def do_OPTIONS(self):self.reply(403,{'error':'Cross-origin requests are not allowed.'})

def make_server(app,port=8765):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.app=app
    return server

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args();app=App()
    try:server=make_server(app,args.port)
    except OSError as exc:parser.exit(1,f'Cannot start the local server; the port may be in use. / 无法启动，端口可能已占用：{exc}\n')
    url=f'http://127.0.0.1:{server.server_port}/#{app.token}'
    print('Local research library / 本地文献库：'+url,flush=True)
    print('Keep this window open. Press Ctrl+C to stop. / 保持此窗口打开，Ctrl+C 停止。',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();app.close()

if __name__=='__main__':main()
