"""Create local configuration or print a portable MCP registration command."""
import argparse,json,shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def mcp_command(root=ROOT):
    parts=['codex','mcp','add','epilepsy_research','--env','HF_HUB_OFFLINE=1','--env','TRANSFORMERS_OFFLINE=1','--env','HF_HUB_DISABLE_TELEMETRY=1','--env','TOKENIZERS_PARALLELISM=false','--',str(root/'.venv/bin/python'),str(root/'mcp_server.py')]
    return shlex.join(parts)

def initialize(root,zotero_dir,collection_name,collection_key=''):
    config=json.loads((root/'config.example.json').read_text())
    config.update(zotero_data_dir=str(Path(zotero_dir).expanduser().resolve()),collection_name=collection_name,collection_key=collection_key)
    # Exclusive creation protects settings on subsequent updates.
    with (root/'config.json').open('x') as f:json.dump(config,f,ensure_ascii=False,indent=2);f.write('\n')
    return root/'config.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zotero-dir',default='~/Zotero');p.add_argument('--collection-name',default='癫痫预测');p.add_argument('--collection-key',default='');p.add_argument('--print-mcp',action='store_true')
    a=p.parse_args()
    if a.print_mcp:print(mcp_command())
    else:
        try:print(initialize(ROOT,a.zotero_dir,a.collection_name,a.collection_key))
        except FileExistsError:p.exit(1,'config.json already exists; edit it explicitly instead of overwriting.\n')
