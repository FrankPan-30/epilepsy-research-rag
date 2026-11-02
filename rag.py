"""Local, source-grounded PDF/Zotero retrieval. No paid APIs or source-file writes."""
from __future__ import annotations
import argparse, collections, contextlib, datetime, fcntl, hashlib, html, importlib.metadata
import json, os, re, sqlite3, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get('RAG_WORKSPACE',str(ROOT))).expanduser().resolve()
DATA = WORKSPACE / 'data'
MODEL = ROOT / 'models' / 'multilingual-e5-small'
def load_config(root=ROOT,settings_root=None):
    config=json.loads((root/'config.example.json').read_text())
    settings_root=Path(settings_root) if settings_root is not None else root
    if (settings_root/'config.json').exists():config.update(json.loads((settings_root/'config.json').read_text()))
    config.setdefault('library_source','zotero')  # Existing configurations keep their source.
    if config['library_source'] not in ('zotero','pdf_folder'):raise ValueError('library_source must be zotero or pdf_folder')
    for key in ('zotero_data_dir','pdf_dir'):
        if config.get(key):config[key]=str(Path(config[key]).expanduser().resolve())
    return config

CFG = load_config(settings_root=WORKSPACE)
PARSER_VERSION = 'pymupdf4llm-0.0.27-v1'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')

FIELDS = {
 'task_data': r'CHB.?MIT|Freiburg|Kaggle|EPILEPSIAE|scalp|intracranial|patients?|subjects?|seizures?',
 'preprocessing': r'band.?pass|notch|sampling|resampl|normaliz|artifact|channels?|overlap|window length',
 'validation': r'leave.one|LOSO|LOPO|cross.patient|patient.independent|cross.validation|validation set|test set|train.test|data leakage',
 'prediction_definition': r'pre.?ictal|inter.?ictal|post.?ictal|prediction horizon|occurrence period|\bSPH\b|\bSOP\b',
 'model_method': r'architecture|transformer|convolution|attention|graph|hypergraph|contrastive|domain adapt|spectral|feature extraction|classifier',
 'history_information': r'historical|history|circadian|multiday|long.term|temporal context|previous seizure',
 'alarm_postprocessing': r'post.process|smooth|moving average|threshold|refractory|cooldown|alarm|k.of.n|consecutive',
 'results_metrics': r'sensitivity|specificity|\bAUC\b|false (?:positive|alarm)|FPR|FA/h|time.in.warning|warning time|prediction time',
 'ablation_limitations': r'ablation|limitation|future work|drawback|failed|failure|trade.off|significan',
}
QUERY_TERMS = {
 '跨患者': 'cross patient patient independent leave one patient LOPOCV',
 '留一患者': 'leave one patient LOPOCV', '留一发作': 'leave one seizure LOSO',
 '误报': 'false alarm false positive FPR', '后处理': 'postprocessing smoothing alarm threshold refractory',
 '平滑': 'smoothing moving average', '阈值': 'threshold calibration',
 '历史信息': 'historical information temporal context previous seizure circadian',
 '模型': 'model architecture', '图网络': 'graph neural network', '超图': 'hypergraph',
 '域适应': 'domain adaptation', '对比学习': 'contrastive learning', '频谱': 'spectral power frequency',
 '发作前期': 'preictal pre ictal', '数据泄漏': 'data leakage validation split',
 '数据质量': 'artifact noise signal quality preprocessing', '消融': 'ablation',
 '不平衡': 'class imbalance', '评价': 'evaluation metrics validation',
 '灵敏度': 'sensitivity', '校准': 'calibration', '泛化': 'generalization patient independent',
 '预警': 'prediction horizon occurrence period alarm warning', '少通道': 'few channels channel selection',
 '邻接矩阵': 'adjacency matrix', '电极': 'electrode', '物理距离': 'physical distance',
 '深度可分离': 'depthwise separable convolution', '单通道': 'single channel',
 '功率谱': 'power spectra spectral parameterization', '通道选择': 'channel selection',
 '自相关': 'autocorrelation', '临界减速': 'critical slowing down', '发作率': 'seizure rate',
 '多时间尺度': 'multiple timescales circadian multidien',
}

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def json_geometry(obj):
    # PyMuPDF uses Rect/Point for layout positions; keep coordinates as arrays.
    if type(obj).__module__=='pymupdf' and type(obj).__name__ in ('Rect','IRect','Point','Quad'):
        return list(obj)
    raise TypeError(f'Unsupported JSON value: {type(obj).__name__}')
def dumps(x): return json.dumps(x, ensure_ascii=False, indent=2,default=json_geometry)
def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(dumps(obj)); tmp.replace(path)
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def plain(x): return html.unescape(re.sub('<[^>]+>', ' ', x or ''))
def keyword_text(text):
    # unicode61 joins adjacent Han and Latin characters into one token.
    return re.sub(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])',' ',text)

def zotero_inventory():
    """Read a consistent SQLite snapshot; fallback when Zotero local API is unavailable."""
    base = Path(CFG['zotero_data_dir'])
    db = sqlite3.connect((base / 'zotero.sqlite').as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
    cols = [dict(r) for r in db.execute('SELECT collectionID,collectionName,parentCollectionID,key FROM collections')]
    if CFG.get('collection_key'):
        scope = {r['collectionID'] for r in cols if r['key'] == CFG['collection_key']}
    else:
        scope = {r['collectionID'] for r in cols if r['collectionName'] == CFG['collection_name']}
        if len(scope)>1:raise ValueError('Collection name is ambiguous; specify collection_key in config.json')
    if not scope: raise ValueError('Configured Zotero collection not found')
    while True:
        new = scope | {r['collectionID'] for r in cols if r['parentCollectionID'] in scope}
        if new == scope: break
        scope = new
    names = {r['collectionID']: r['collectionName'] for r in cols}
    active = {r['itemID']: dict(r) for r in db.execute('SELECT i.*,t.typeName FROM items i JOIN itemTypes t USING(itemTypeID) WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)')}
    members = collections.defaultdict(list)
    for col, i in db.execute('SELECT collectionID,itemID FROM collectionItems'):
        if col in scope and i in active: members[i].append(names[col])
    fields = collections.defaultdict(dict)
    for i, f, v in db.execute('SELECT d.itemID,f.fieldName,v.value FROM itemData d JOIN fields f USING(fieldID) JOIN itemDataValues v USING(valueID)'):
        fields[i][f] = v
    authors, tags, attachments, notes = (collections.defaultdict(list) for _ in range(4))
    for i, first, last in db.execute('SELECT ic.itemID,c.firstName,c.lastName FROM itemCreators ic JOIN creators c USING(creatorID) ORDER BY ic.orderIndex'):
        authors[i].append((first+' '+last).strip())
    for i, t in db.execute('SELECT it.itemID,t.name FROM itemTags it JOIN tags t USING(tagID)'): tags[i].append(t)
    for r in db.execute("SELECT * FROM itemAttachments WHERE contentType='application/pdf'"):
        if r['itemID'] not in active: continue
        a = dict(r); key = active[a['itemID']]['key']; p = a['path'] or ''
        path = base / 'storage' / key / p[8:] if p.startswith('storage:') else Path(p)
        exists = bool(p) and not p.startswith('attachments:') and path.is_file()
        attachments[a['parentItemID']].append({'key':key, 'path':str(path), 'exists':exists, 'bytes':path.stat().st_size if exists else 0})
    for i, parent, text in db.execute('SELECT itemID,parentItemID,note FROM itemNotes'):
        if i in active: notes[parent].append({'key':active[i]['key'],'text':plain(text),'kind':'user_note'})
    attachment_parents = {r[0]:r[1] for r in db.execute('SELECT itemID,parentItemID FROM itemAttachments')}
    for r in db.execute('SELECT * FROM itemAnnotations'):
        if r['itemID'] not in active: continue
        parent = attachment_parents.get(r['parentItemID'])
        notes[parent].append({'key':active[r['itemID']]['key'], 'text':(r['text'] or '')+'\nComment: '+(r['comment'] or ''), 'kind':'user_annotation', 'page_label':r['pageLabel']})
    papers = []
    for i in sorted(members):
        if active[i]['typeName'] in ('attachment','note','annotation'): continue
        f = fields[i]; papers.append({'key':active[i]['key'],'title':f.get('title',''), 'authors':authors[i], 'date':f.get('date',''), 'doi':f.get('DOI',''), 'journal':f.get('publicationTitle',''), 'abstract':f.get('abstractNote',''), 'item_type':active[i]['typeName'], 'collections':members[i], 'tags':tags[i], 'attachments':attachments[i], 'notes':notes[i], 'version':active[i]['version']})
    db.rollback(); db.close()
    for paper in papers:paper.update(library_source='zotero',metadata_quality='zotero_metadata_unreviewed')
    return papers

def inventory():
    if CFG.get('library_source','zotero')=='zotero':return zotero_inventory()
    if CFG['library_source']=='pdf_folder':
        from pdf_source import pdf_inventory
        return pdf_inventory(CFG.get('pdf_dir',''))
    raise ValueError('library_source must be zotero or pdf_folder')

def citation_for(paper,attachment,page,kind):
    source=paper.get('library_source','zotero')
    cite={'paper_key':paper['key'],'title':paper['title'],'authors':paper['authors'],'date':paper['date'],
          'doi':paper['doi'],'pdf_page':page,'attachment_key':attachment.get('key'),'source_kind':kind,'library_source':source}
    if attachment.get('path'):
        cite['pdf_path']=attachment['path']
        cite['file_url']=Path(attachment['path']).resolve().as_uri()+f'#page={page or 1}'
    if source=='zotero':
        cite['zotero_url']=(f"zotero://open-pdf/library/items/{attachment['key']}?page={page or 1}" if attachment.get('path')
                            else f"zotero://select/library/items/{paper['key']}")
    return cite

def parse_pdf(a):
    import pymupdf, pymupdf4llm
    digest = sha(a['path']); dest = DATA / 'parsed' / (a['key']+'.json')
    if a.get('sha256') and a['sha256']!=digest:raise ValueError('PDF changed during inventory; run sync again')
    if dest.exists():
        cached = json.loads(dest.read_text())
        if cached['sha256']==digest and cached['parser']==PARSER_VERSION:
            return enrich_layout(a,cached,dest)
    with contextlib.redirect_stdout(sys.stderr):
        pages = pymupdf4llm.to_markdown(a['path'], page_chunks=True, show_progress=False, write_images=False)
    result = {'key':a['key'],'sha256':digest,'parser':PARSER_VERSION,'pages':[]}
    with pymupdf.open(a['path']) as doc:
        if len(pages) != len(doc): raise ValueError('Page mapping mismatch')
        for idx, row in enumerate(pages):
            page = doc[idx]; text = row['text']
            result['pages'].append({'page':idx+1, 'page_label':page.get_label(), 'text':text, 'tables':row.get('tables',[]), 'images':row.get('images',[]), 'quality':'needs_ocr_or_visual_check' if len(re.sub(r'\s','',text))<100 else 'text_extracted_unreviewed'})
    result=enrich_layout(a,result,dest)
    (DATA/'parsed'/f"{a['key']}.md").write_text('\n\n'.join(f"<!-- PDF page {p['page']} -->\n{p['text']}" for p in result['pages']))
    return result

_ocr_engine=None
def table_regions(page):
    """Locate caption-led column regions; keep original image for column verification."""
    import pymupdf
    blocks=page.get_text('blocks')
    regions=[];w=page.rect.width;h=page.rect.height
    for b in blocks:
        if not re.search(r'(?im)^TABLE\s+[IVX\d]+\b',b[4]):continue
        center=(b[0]+b[2])/2
        left,right=(0,w/2) if center<w*.45 else ((w/2,w) if center>w*.55 else (0,w))
        top=max(0,b[1]-3)
        ends=[other[1] for other in blocks if other[1]>b[3]+35 and left<=other[0]<right and len(other[4])>160]
        bottom=min(ends+[h-15])
        if bottom>top:regions.append(pymupdf.Rect(left,top,right,bottom))
    return regions

def enrich_layout(a,result,dest):
    global _ocr_engine
    if result.get('enrichment_version')==2:return result
    import pymupdf
    with pymupdf.open(a['path']) as doc:
        for p in result['pages']:
            page=doc[p['page']-1]
            p['native_text']=page.get_text(sort=True)
            captions=len(re.findall(r'(?im)^\s*(?:\*\*)?TABLE\s+[IVX\d]+\b',p['text']))
            needs=p['quality'].startswith('needs_') or (captions>len(p['tables']))
            p['ocr_required']=needs
            if needs:
                p['quality']='image_table_or_low_text_needs_visual_check'
                regions=table_regions(page) if captions else [page.rect]
                regions=regions or [page.rect]
                p['native_table_text']='\n\n'.join(page.get_text(clip=r,sort=True) for r in regions)
                # Native table cells need layout review, but do not need OCR again.
                image_regions=[r for r in regions if len(re.findall(r'\b\d+(?:\.\d+)?\b',page.get_text(clip=r)))<6]
                if p.get('ocr_text'):continue  # retain already completed full-page OCR
                if not image_regions:continue
                try:
                    if _ocr_engine is None:
                        import onnxruntime
                        onnxruntime.disable_telemetry_events()
                        from rapidocr_onnxruntime import RapidOCR
                        _ocr_engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
                    lines=[]
                    for region in image_regions:
                        with tempfile.TemporaryDirectory(prefix='epilepsy-rag-ocr-') as temp:
                            png=Path(temp)/'page.png';page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=region).save(png)
                            rows,_=_ocr_engine(str(png))
                        lines.extend({'bbox':box,'text':text,'recognizer_score':float(score),'pdf_region':list(region),'render_scale':2} for box,text,score in (rows or []))
                    p['ocr_lines']=lines
                    p['ocr_text']='\n'.join(x['text'] for x in p['ocr_lines'])
                    p['ocr_engine']='rapidocr_onnxruntime-1.4.4'
                    if not lines:p['ocr_error']='OCR returned no text'
                except Exception as exc:p['ocr_error']=str(exc)
    result['enrichment_version']=2
    write_json(dest,result)
    return result

def parse_worker(a):
    try:
        result=parse_pdf(a)
        return a['key'],len(result['pages']),None
    except Exception as exc:return a['key'],0,str(exc)

_model = None
def model():
    global _model
    if _model is None:
        provenance=json.loads((MODEL/'local_provenance.json').read_text())
        if provenance['repo']!=CFG['embedding_model']:
            raise ValueError('Configured embedding model differs from local weights; install matching model and rebuild')
        from sentence_transformers import SentenceTransformer
        import torch
        torch.set_num_threads(min(6,os.cpu_count() or 4))
        _model = SentenceTransformer(str(MODEL), device='cpu', local_files_only=True)
    return _model

def chunks_for(text, tokenizer, limit=None):
    """Token-aware windows with original character offsets, never silent truncation."""
    limit = limit or CFG['chunk_tokens']
    reference_heading=r'R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S'
    parts = re.split(r'(?m)(?=^#{1,6} |^'+reference_heading+r'\s*$)',text)
    section = ''
    for part in parts:
        head = re.match(r'^(#{1,6})\s+(.+)', part)
        if head: section=head[2].strip()
        elif re.match(reference_heading+r'\s*(?:\n|$)',part):section='References'
        enc=tokenizer(part,add_special_tokens=False,return_offsets_mapping=True,truncation=False)
        offsets=enc['offset_mapping']; pos=0
        while pos<len(offsets):
            end=min(pos+limit,len(offsets))
            snippet=part[offsets[pos][0]:offsets[end-1][1]].strip()
            if snippet: yield section,snippet
            if end==len(offsets):break
            pos=end-CFG['overlap_tokens']

SCHEMA = '''
CREATE TABLE papers(key TEXT PRIMARY KEY, title TEXT, metadata TEXT);
CREATE TABLE chunks(id INTEGER PRIMARY KEY, paper_key TEXT, attachment_key TEXT, page INTEGER, section TEXT, kind TEXT, text TEXT, citation TEXT, quality TEXT);
CREATE VIRTUAL TABLE search USING fts5(title, text, tokenize='porter unicode61');
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
'''

def build(skip_vectors=False):
    DATA.mkdir(parents=True,exist_ok=True)
    with open(WORKSPACE/'.build.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        papers=inventory()
        from concurrent.futures import ProcessPoolExecutor,as_completed
        attachments={a['key']:a for p in papers for a in p['attachments'] if a['exists']}
        with ProcessPoolExecutor(max_workers=3) as workers:
            jobs=[workers.submit(parse_worker,a) for a in attachments.values()]
            for n,job in enumerate(as_completed(jobs),1):
                key,pages,error=job.result()
                print(f'PDF {n}/{len(jobs)} {key}: {error or str(pages)+" pages"}',file=sys.stderr,flush=True)
        # Stage everything in a generation directory; publish a single atomic pointer.
        generation=DATA/('generation-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        generation.mkdir()
        db=sqlite3.connect(generation/'library.sqlite'); db.executescript(SCHEMA)
        tokenizer=model().tokenizer
        manifest={'started_at':stamp(),'papers':len(papers),'pdfs':0,'pages':0,'failed_pdfs':[], 'low_text_pages':[], 'ocr_pages':0,'ocr_failed_pages':[],'parser':PARSER_VERSION,'embedding_model':CFG['embedding_model'],'config':CFG}
        manifest['library_source']=CFG.get('library_source','zotero')
        manifest['duplicate_pdfs_skipped']=sum(len(p.get('duplicate_paths',[])) for p in papers)
        manifest['metadata_only_papers']=sum(not any(a['exists'] for a in p['attachments']) for p in papers)
        texts=[]; cards=[]
        def add(p,a,page,section,kind,text,quality):
            cite=citation_for(p,a,page,kind)
            idx=len(texts)+1
            db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)',(idx,p['key'],a.get('key'),page,section,kind,text,dumps(cite),quality))
            db.execute('INSERT INTO search(rowid,title,text) VALUES(?,?,?)',(idx,keyword_text(p['title']),keyword_text(text)))
            # Title context is capped to preserve the body within E5's 512-token limit.
            title=tokenizer.decode(tokenizer.encode(p['title'],add_special_tokens=False)[:45])
            texts.append('passage: '+title+'\n'+text)
            return idx
        for n,p in enumerate(papers,1):
            db.execute('INSERT INTO papers VALUES(?,?,?)',(p['key'],p['title'],dumps(p)))
            for section,text in chunks_for(p['title']+'\n'+p['abstract'],tokenizer):
                add(p,{},None,'Bibliographic record','metadata',text,p.get('metadata_quality','zotero_metadata_unreviewed'))
            card={'paper_key':p['key'],'title':p['title'],'status':'candidate_evidence_not_verified_facts','fields':{k:[] for k in FIELDS},'missing_fulltext':True}
            for a in p['attachments']:
                if not a['exists']:continue
                try: parsed=parse_pdf(a)
                except Exception as exc:
                    manifest['failed_pdfs'].append({'attachment':a['key'],'error':str(exc)})
                    print(f"PDF FAILED {a['key']}: {exc}",file=sys.stderr,flush=True);continue
                card['missing_fulltext']=False;manifest['pdfs']+=1
                previous_section=''
                for page in parsed['pages']:
                    manifest['pages']+=1
                    if page['quality']!='text_extracted_unreviewed': manifest['low_text_pages'].append({'attachment':a['key'],'page':page['page']})
                    for section,text in chunks_for(page['text'],tokenizer):
                        section=section or previous_section
                        previous_section=section
                        kind='references' if re.search(r'^(?:\d+[. ]*)?references$',section,re.I) else 'fulltext'
                        idx=add(p,a,page['page'],section,kind,text,page['quality'])
                        if kind=='references':continue
                        for field,pattern in FIELDS.items():
                            if re.search(pattern,text,re.I):card['fields'][field].append({'chunk_id':idx,'attachment_key':a['key'],'page':page['page']})
                    if page.get('ocr_text'):
                        manifest['ocr_pages']+=1
                        for _,text in chunks_for(page['ocr_text'],tokenizer):add(p,a,page['page'],'OCR text; verify table columns on original page','ocr',text,'ocr_unverified_reading_order')
                    if page.get('native_table_text'):
                        for _,text in chunks_for(page['native_table_text'],tokenizer):add(p,a,page['page'],'Native table region; verify column alignment','layout_text',text,'native_text_unverified_table_structure')
                    if page.get('ocr_error'):manifest['ocr_failed_pages'].append({'attachment':a['key'],'page':page['page'],'error':page['ocr_error']})
            for note in p['notes']:
                for section,text in chunks_for(note['text'],tokenizer):add(p,{},None,section,note['kind'],text,'user_annotation_not_author_claim')
            cards.append(card)
            print(f"[{n}/{len(papers)}] {p['key']} {p['title'][:65]}",file=sys.stderr,flush=True)
        # Curated project guidance is explicitly separated from paper evidence.
        for path in sorted((ROOT/'knowledge').glob('*.md')):
            p={'key':'LOCAL:'+path.stem,'title':path.stem,'authors':[],'date':'','doi':'','library_source':'project'}
            db.execute('INSERT INTO papers VALUES(?,?,?)',(p['key'],p['title'],dumps(p)))
            for section,text in chunks_for(path.read_text(),tokenizer):add(p,{},None,section,'project_guidance',text,'project_rule_not_literature_evidence')
        manifest['chunks']=len(texts)
        if not skip_vectors:
            import numpy as np
            print(f'Embedding {len(texts)} chunks locally...',file=sys.stderr,flush=True)
            cache=sqlite3.connect(DATA/'embedding_cache.sqlite')
            cache.execute('CREATE TABLE IF NOT EXISTS vectors(hash TEXT PRIMARY KEY, vector BLOB)')
            revision=json.loads((MODEL/'local_provenance.json').read_text())['revision']
            hashes=[hashlib.sha256((revision+'\n'+t).encode()).hexdigest() for t in texts]
            cached={r[0]:np.frombuffer(r[1],dtype='float32') for r in cache.execute('SELECT hash,vector FROM vectors')}
            missing=list(dict.fromkeys(h for h in hashes if h not in cached));by_hash=dict(zip(hashes,texts))
            manifest['embeddings_reused']=len(texts)-len(missing)
            if missing:
                encoded=model().encode([by_hash[h] for h in missing],batch_size=24,normalize_embeddings=True,show_progress_bar=True)
                for h,v in zip(missing,encoded):
                    cached[h]=v.astype('float32');cache.execute('INSERT OR REPLACE INTO vectors VALUES(?,?)',(h,cached[h].tobytes()))
                cache.commit()
            vectors=np.stack([cached[h] for h in hashes]);cache.close()
            np.save(generation/'vectors.npy',vectors.astype('float32'))
            manifest['vector_shape']=list(vectors.shape)
            manifest['embedding_revision']=revision
        manifest['completed_at']=stamp()
        for k,v in manifest.items():db.execute('INSERT INTO meta VALUES(?,?)',(k,json.dumps(v,ensure_ascii=False)))
        db.commit();db.close()
        write_json(generation/'cards.json',cards);write_json(generation/'manifest.json',manifest)
        write_json(generation/'inventory.json',papers)
        write_json(DATA/'inventory.json',papers)  # Legacy inventory location, written only after a successful build.
        write_json(DATA/'current.json',{'generation':generation.name})
        print(dumps(manifest))

class Library:
    def __init__(self,data_dir=None):
        self.data=Path(data_dir).resolve() if data_dir is not None else DATA
        self.folder=self.data/json.loads((self.data/'current.json').read_text())['generation']
        self.db=sqlite3.connect((self.folder/'library.sqlite').as_uri()+'?mode=ro',uri=True,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.vectors=None
    def status(self):return json.loads((self.folder/'manifest.json').read_text())
    def evidence(self,row):
        d=dict(row);d['citation']=json.loads(d['citation']);d['generation']=self.folder.name;return d
    def read(self,chunk_id,neighbors=0):
        r=self.db.execute('SELECT * FROM chunks WHERE id=?',(chunk_id,)).fetchone()
        if r is None:raise ValueError('Unknown chunk ID')
        rows=[r]
        if neighbors:
            rows=self.db.execute('SELECT * FROM chunks WHERE paper_key=? AND attachment_key IS ? AND page BETWEEN ? AND ? ORDER BY page,id',(r['paper_key'],r['attachment_key'],(r['page'] or 0)-neighbors,(r['page'] or 0)+neighbors)).fetchall() or [r]
        return [self.evidence(x) for x in rows]
    def search(self,query,limit=8,paper_key=None,source='papers',mode='hybrid',collection=None,year_min=None,year_max=None):
        if not query.strip():raise ValueError('Query must not be empty')
        limit=max(1,min(limit,40)); pool=CFG['candidates_per_route']
        expanded=query+' '+' '.join(v for k,v in QUERY_TERMS.items() if k in query)
        terms=list(dict.fromkeys(re.findall(r'[A-Za-z0-9][A-Za-z0-9-]*',expanded)))
        terms=[x for x in terms if x.lower() not in {'the','a','and','of','in','for','to','is','how','what','does','with','are'}]
        where=['1=1'];args=[]
        if paper_key:where.append('c.paper_key=?');args.append(paper_key)
        if source=='papers':where.append("c.kind IN ('metadata','fulltext','ocr','layout_text')")
        elif source=='project':where.append("c.kind='project_guidance'")
        elif source!='all':raise ValueError('source must be papers/project/all')
        if collection or year_min or year_max:
            allowed=[]
            for record in self.db.execute('SELECT key,metadata FROM papers'):
                meta=json.loads(record['metadata'])
                if collection and not any(collection.casefold() in c.casefold() for c in meta.get('collections',[])):continue
                match=re.search(r'\b(?:19|20)\d{2}\b',meta.get('date',''))
                year=int(match[0]) if match else None
                if (year_min or year_max) and year is None:continue
                if year_min and year<year_min:continue
                if year_max and year>year_max:continue
                allowed.append(record['key'])
            where.append('c.paper_key IN ('+','.join('?' for _ in allowed)+')');args.extend(allowed)
        condition=' AND '.join(where)
        eligible=self.db.execute('SELECT c.* FROM chunks c WHERE '+condition,args).fetchall()
        rows={r['id']:r for r in eligible}; ranked=[]
        if terms:
            match=' OR '.join('"'+t+'"' for t in terms[:60])
            hits=self.db.execute('SELECT c.id,bm25(search,2.0,1.0) rank FROM search JOIN chunks c ON c.id=search.rowid WHERE search MATCH ? AND '+condition+' ORDER BY rank LIMIT ?',[match,*args,pool]).fetchall()
            ranked.append([r['id'] for r in hits])
        dense_scores={}
        if mode=='hybrid':
            import numpy as np
            status=self.status()
            provenance=json.loads((MODEL/'local_provenance.json').read_text())
            if provenance['revision']!=status['embedding_revision']:
                raise ValueError('Embedding model revision changed; rebuild index before querying')
            if self.vectors is None:self.vectors=np.load(self.folder/'vectors.npy',mmap_mode='r')
            q=model().encode(['query: '+query],normalize_embeddings=True)[0]
            keys=np.array(list(rows),dtype=int)
            if len(keys):
                # Explicit contraction avoids spurious Accelerate matmul warnings
                # on Apple Silicon with the pinned NumPy (numpy/numpy#28687).
                scores=np.einsum('ij,j->i',self.vectors[keys-1],q,optimize=False)
                if not np.isfinite(scores).all():raise ValueError('Non-finite similarity scores; check model and index')
                order=np.argsort(-scores)[:pool]
                ranked.append([int(keys[i]) for i in order]);dense_scores={int(keys[i]):float(scores[i]) for i in order}
        elif mode!='keyword':raise ValueError('mode must be hybrid/keyword')
        fused=collections.defaultdict(float)
        for route in ranked:
            for rank,key in enumerate(route,1):fused[key]+=1/(60+rank)
        # RRF is rank fusion, not a trained cross-encoder; score is not confidence.
        selected=[];per_paper=collections.Counter()
        for key in sorted(fused,key=lambda k:(-fused[k],k)):
            row=rows[key]
            if not paper_key and per_paper[row['paper_key']]>=CFG['max_per_paper']:continue
            d=self.evidence(row);d['rank_score']=fused[key];d['semantic_score']=dense_scores.get(key)
            selected.append(d);per_paper[row['paper_key']]+=1
            if len(selected)>=limit:break
        return {'query':query,'expanded_keywords':expanded,'mode':mode,'generation':self.folder.name,'candidate_routes':[len(r) for r in ranked], 'exhaustive':False,'results':selected,'warning':'Ranked retrieval is not an exhaustive review or a proof of absence. Scores are not evidence confidence.'}
    def paper(self,key):
        r=self.db.execute('SELECT metadata FROM papers WHERE key=?',(key,)).fetchone()
        if r is None:raise ValueError('Unknown paper key')
        card=next((x for x in json.loads((self.folder/'cards.json').read_text()) if x['paper_key']==key),None)
        reviewed=self.data/'reviews'/(key+'.json')
        review=json.loads(reviewed.read_text()) if reviewed.exists() else None
        if review:
            review['matches_indexed_pdf_version']=all(json.loads((self.data/'parsed'/(x['attachment_key']+'.json')).read_text())['sha256']==x['pdf_sha256'] for x in review['claims'])
        return {'metadata':json.loads(r[0]),'evidence_map':card,'checked_method_notes':review,'generation':self.folder.name}
    def catalog(self,query='',field=None):
        cards={c['paper_key']:c for c in json.loads((self.folder/'cards.json').read_text())}
        if field and field not in FIELDS:raise ValueError('Unknown field')
        out=[]
        for r in self.db.execute('SELECT * FROM papers ORDER BY title'):
            if r['key'].startswith('LOCAL:'):continue
            p=json.loads(r['metadata']);card=cards.get(r['key'],{})
            if query and query.casefold() not in json.dumps(p,ensure_ascii=False).casefold():continue
            out.append({'key':r['key'],'title':r['title'],'date':p.get('date'),'doi':p.get('doi'),'collections':p.get('collections',[]),'fulltext_available':not card.get('missing_fulltext',True),'candidate_evidence_count':len(card.get('fields',{}).get(field,[])) if field else None})
        return {'total':len(out),'papers':out,'field':field,'note':'Field matches are keyword-located candidates; zero means not located, not absent. Inspect evidence before classifying a study.'}

    def page(self,attachment_key,page):
        # Resolve only attachments in the indexed collection, never arbitrary paths.
        r=self.db.execute('SELECT citation FROM chunks WHERE attachment_key=? LIMIT 1',(attachment_key,)).fetchone()
        if not r:raise ValueError('Attachment is outside the indexed corpus')
        cite=json.loads(r[0]);parsed=json.loads((self.data/'parsed'/(attachment_key+'.json')).read_text())
        if page<1 or page>len(parsed['pages']):raise ValueError('Page out of range')
        cite['pdf_page']=page
        if cite.get('pdf_path'):cite['file_url']=Path(cite['pdf_path']).resolve().as_uri()+f'#page={page}'
        if 'zotero_url' in cite:cite['zotero_url']=f'zotero://open-pdf/library/items/{attachment_key}?page={page}'
        return {'citation':cite,'page':parsed['pages'][page-1]}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('sync');sub.add_parser('status');sub.add_parser('inventory')
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--limit',type=int,default=8);s.add_argument('--paper');s.add_argument('--source',choices=['papers','project','all'],default='papers');s.add_argument('--keyword-only',action='store_true')
    s.add_argument('--collection');s.add_argument('--year-min',type=int);s.add_argument('--year-max',type=int)
    r=sub.add_parser('read');r.add_argument('chunk',type=int);r.add_argument('--neighbors',type=int,default=0)
    r=sub.add_parser('paper');r.add_argument('key')
    r=sub.add_parser('catalog');r.add_argument('--query',default='');r.add_argument('--field',choices=list(FIELDS))
    a=p.parse_args()
    if a.cmd=='sync':build();return
    if a.cmd=='inventory':print(dumps(inventory()));return
    lib=Library()
    if a.cmd=='status':out=lib.status()
    elif a.cmd=='search':out=lib.search(a.query,a.limit,a.paper,a.source,'keyword' if a.keyword_only else 'hybrid',a.collection,a.year_min,a.year_max)
    elif a.cmd=='read':out=lib.read(a.chunk,max(0,min(2,a.neighbors)))
    elif a.cmd=='paper':out=lib.paper(a.key)
    else:out=lib.catalog(a.query,a.field)
    print(dumps(out))

if __name__=='__main__':main()
