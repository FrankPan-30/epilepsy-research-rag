"""Try the real keyword retrieval path with synthetic notes. No downloads or API calls."""
import argparse,json,sqlite3,tempfile
from pathlib import Path
from rag import Library,SCHEMA,keyword_text

NOTES=[
    ('DEMO-ALARM','Synthetic note: alarm postprocessing',
     'Record false alarm rate together with threshold, smoothing, consecutive confirmation, and refractory period. Compare alarm settings under the same evaluation protocol.'),
    ('DEMO-SPLIT','Synthetic note: validation protocol',
     'For this synthetic example, leave-one-patient-out (LOPOCV) holds out a patient. Track training, validation, and test assignments before making overlapping windows.'),
    ('DEMO-METHOD','Synthetic note: method comparison',
     'A method summary records the research question, model architecture, inputs, ablation evidence, and limitations. Read the original passage before transferring a claim.')
]

def run_demo(query='误报后处理中的平滑和阈值',limit=3):
    with tempfile.TemporaryDirectory(prefix='epilepsy-rag-demo-') as temp:
        root=Path(temp);folder=root/'synthetic-demo';folder.mkdir()
        (root/'current.json').write_text(json.dumps({'generation':folder.name}))
        db=sqlite3.connect(folder/'library.sqlite');db.executescript(SCHEMA)
        for index,(key,title,text) in enumerate(NOTES,1):
            meta={'key':key,'title':title,'authors':[],'date':'','doi':''}
            cite={'paper_key':key,'title':title,'source_kind':'synthetic_demo','pdf_page':None,'notice':'Synthetic fixture, not a scientific paper or result.'}
            db.execute('INSERT INTO papers VALUES(?,?,?)',(key,title,json.dumps(meta)))
            db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)',(index,key,None,None,'Demo','synthetic_demo',text,json.dumps(cite),'synthetic_not_scientific_evidence'))
            db.execute('INSERT INTO search(rowid,title,text) VALUES(?,?,?)',(index,keyword_text(title),keyword_text(text)))
        db.commit();db.close()
        library=Library(data_dir=root)
        try:return library.search(query,limit=limit,source='all',mode='keyword')
        finally:library.db.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query',nargs='?',default='误报后处理中的平滑和阈值')
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run_demo(args.query)
    if args.check:
        assert run_demo()['results'][0]['paper_key']=='DEMO-ALARM'
        assert run_demo('LOPOCV validation')['results'][0]['paper_key']=='DEMO-SPLIT'
        assert not run_demo('zzzzunmatchedtoken')['results']
        print('Synthetic demo checks passed.');return
    print('SYNTHETIC DEMO | keyword retrieval | no model download | no API call')
    print('Question:',args.query)
    for rank,row in enumerate(result['results'],1):
        print(f"\n{rank}. {row['citation']['title']} [{row['paper_key']}]")
        print(row['text'])
    if not result['results']:print('No matching synthetic notes. Try: alarm, LOPOCV, or model architecture.')
    print('\nThese are toy notes, not papers or clinical evidence. Add a PDF folder or Zotero collection for real research.')

if __name__=='__main__':main()
