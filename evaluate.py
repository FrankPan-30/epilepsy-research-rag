"""Small source-anchored retrieval check; does not score generated-answer quality."""
import json,time
from rag import ROOT,DATA,Library,write_json,stamp

def evaluate():
    lib=Library();out=[]
    cases=json.loads((ROOT/'evaluation_cases.json').read_text())
    for c in cases:
        page=lib.page(c['attachment'],c['page'])['page']['text']
        anchor_ok=c['anchor'].casefold() in page.casefold()
        for mode in ['keyword','hybrid']:
            start=time.monotonic();r=lib.search(c['query'],limit=12,mode=mode)
            papers=list(dict.fromkeys(x['paper_key'] for x in r['results']))
            out.append({'id':c['id'],'mode':mode,'anchor_verified':anchor_ok,'target_paper_retrieved':c['paper'] in papers,'target_paper_rank':papers.index(c['paper'])+1 if c['paper'] in papers else None,'seconds':round(time.monotonic()-start,3),'retrieved_papers':papers})
    report={'time':stamp(),'generation':lib.folder.name,'cases':len(cases),'scope':'Eight targeted paper-retrieval checks with source anchors. Development set, not independent performance estimate or answer-quality evaluation. 12 chunks per query. First hybrid query includes model load.','results':out}
    for mode in ['keyword','hybrid']:
        subset=[r for r in out if r['mode']==mode]
        report[mode+'_target_hits']=sum(r['target_paper_retrieved'] for r in subset)
    write_json(DATA/'validation/retrieval.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':evaluate()
