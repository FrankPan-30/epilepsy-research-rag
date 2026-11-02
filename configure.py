"""Create local configuration or print a portable MCP registration command."""
import argparse,json,shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MCP_ENV={'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false'}

def mcp_config(root=ROOT,client='generic'):
    root=Path(root).expanduser().absolute()
    server={'command':str(root/'.venv/bin/python'),'args':[str(root/'mcp_server.py')],'env':dict(MCP_ENV)}
    if client=='vscode':return {'servers':{'epilepsy_research':{'type':'stdio',**server}}}
    if client=='cursor':server={'type':'stdio',**server}
    if client not in ('generic','claude-desktop','cursor'):raise ValueError('Unknown MCP configuration client')
    return {'mcpServers':{'epilepsy_research':server}}

def mcp_command(root=ROOT):
    server=mcp_config(root)['mcpServers']['epilepsy_research']
    parts=['codex','mcp','add','epilepsy_research']
    for key,value in server['env'].items():parts.extend(['--env',key+'='+value])
    parts.extend(['--',server['command'],*server['args']])
    return shlex.join(parts)

def initialize(root,zotero_dir='~/Zotero',collection_name='癫痫预测',collection_key='',pdf_dir=None):
    config=json.loads((root/'config.example.json').read_text())
    config.update(zotero_data_dir=str(Path(zotero_dir).expanduser().resolve()),collection_name=collection_name,collection_key=collection_key)
    config['library_source']='pdf_folder' if pdf_dir is not None else 'zotero'
    if pdf_dir is not None:config['pdf_dir']=str(Path(pdf_dir).expanduser().resolve())
    # Exclusive creation protects settings on subsequent updates.
    with (root/'config.json').open('x') as f:json.dump(config,f,ensure_ascii=False,indent=2);f.write('\n')
    return root/'config.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group()
    source.add_argument('--zotero-dir',default='~/Zotero');source.add_argument('--pdf-dir',help='Recursively index a PDF folder without Zotero')
    p.add_argument('--collection-name',default='癫痫预测');p.add_argument('--collection-key',default='');p.add_argument('--print-mcp',action='store_true')
    p.add_argument('--mcp-client',choices=['codex','claude-desktop','cursor','vscode','generic'],default='codex')
    a=p.parse_args()
    if a.print_mcp:print(mcp_command() if a.mcp_client=='codex' else json.dumps(mcp_config(client=a.mcp_client),ensure_ascii=False,indent=2))
    else:
        try:print(initialize(ROOT,a.zotero_dir,a.collection_name,a.collection_key,pdf_dir=a.pdf_dir))
        except FileExistsError:p.exit(1,'config.json already exists; edit it explicitly instead of overwriting.\n')
