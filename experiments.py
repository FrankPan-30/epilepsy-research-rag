"""Explicit local experiment records. No automatic ingestion of existing projects."""
import argparse, datetime, json, re
from pathlib import Path
from rag import DATA, dumps, write_json

TEMPLATE={'id':'example-experiment','status':'planned','question':'','hypothesis':'','rival_explanations':[],'baseline':'','change':'','dataset_version':'','split_protocol':'','seeds':[],'code_commit':'','configuration':{},'alarm_rules':{},'window_metrics':{},'event_metrics':{},'evaluation_hours':None,'result_paths':[],'conclusion':'','evidence_links':[]}

def save(record):
    for k in ['id','status','question','hypothesis','split_protocol']:
        if not record.get(k):raise ValueError('Required: '+k)
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',record['id']):raise ValueError('Invalid id')
    if record['status'] not in ['planned','running','completed','failed']:raise ValueError('Invalid status')
    if record['status']=='completed' and (not record.get('result_paths') or not record.get('code_commit')):raise ValueError('Completed experiments need result_paths and code_commit')
    record={**TEMPLATE,**record,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    dest=DATA/'experiments'/record['id'];dest.mkdir(parents=True,exist_ok=True)
    write_json(dest/(record['updated_at'].replace(':','-')+'.json'),record)
    write_json(dest/'current.json',record);return record

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('template');s.add_parser('list');a=s.add_parser('save');a.add_argument('file',type=Path)
    a=p.parse_args()
    if a.cmd=='template':out=TEMPLATE
    elif a.cmd=='save':out=save(json.loads(a.file.read_text(encoding='utf-8')))
    else:out=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((DATA/'experiments').glob('*/current.json'))]
    print(dumps(out))
