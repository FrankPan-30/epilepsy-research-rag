"""Run checks once and retain a compact reproducible validation report."""
import json,subprocess,sys,time
from pathlib import Path
from rag import ROOT,DATA,Library,write_json,stamp

def size(path):return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())

if __name__=='__main__':
    dest=DATA/'validation';dest.mkdir(parents=True,exist_ok=True)
    steps=[]
    for name,args in [('tests',['-m','unittest','discover','-s',str(ROOT),'-p','tests.py','-v']),('retrieval',[str(ROOT/'evaluate.py')]),('mcp',[str(ROOT/'check_mcp.py')])]:
        start=time.monotonic()
        with open(dest/(name+'.log'),'w',encoding='utf-8') as log:
            run=subprocess.run([sys.executable,*args],stdout=log,stderr=subprocess.STDOUT)
        steps.append({'name':name,'exit_code':run.returncode,'seconds':round(time.monotonic()-start,2)})
        print(name,run.returncode,flush=True)
        if run.returncode:raise SystemExit('Check failed; inspect '+str(dest/(name+'.log')))
    lib=Library();status=lib.status()
    report={'time':stamp(),'steps':steps,'corpus':status,'disk_bytes':{name:size(ROOT/name) for name in ['data','models','.venv']},'additional_paid_cloud_api_calls':0,'reviewed_method_notes':len(list((DATA/'reviews').glob('*.json'))),'limitations':['Eight targeted retrieval checks are a development set, not an independent answer-quality estimate.','22 further research acceptance questions await real-use review.','Parsed text, OCR and keyword evidence maps have not all been manually verified.','Existing personal experiment results have not been bulk imported.']}
    write_json(dest/'summary.json',report)
    print(json.dumps({k:report[k] for k in ['time','steps','disk_bytes','additional_paid_cloud_api_calls']},ensure_ascii=False,indent=2))
