"""Exercise actual stdio MCP transport and evidence tools end to end."""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from rag import ROOT,DATA,Library,write_json,stamp

async def check():
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'mcp_server.py')],env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize();listed=await session.list_tools()
            assert len(listed.tools)==9
            result=await session.call_tool('research_workflow',{'task':'quality'})
            assert not result.isError
            report={'time':stamp(),'tools':[t.name for t in listed.tools],'workflow_ok':True}
            if (DATA/'current.json').exists():
                result=await session.call_tool('knowledge_status',{})
                assert not result.isError;report['status_ok']=True
                library=Library()
                try:
                    record=library.db.execute("SELECT p.key,p.title,c.attachment_key,c.page FROM papers p JOIN chunks c ON c.paper_key=p.key WHERE c.attachment_key IS NOT NULL AND c.page IS NOT NULL ORDER BY c.id LIMIT 1").fetchone()
                finally:library.db.close()
                if record is None:raise ValueError('MCP image check needs at least one successfully indexed PDF')
                result=await session.call_tool('search_literature',{'query':record['title'] or 'research methods','paper_key':record['key'],'limit':5})
                assert not result.isError
                payload=result.structuredContent or json.loads(next(c.text for c in result.content if c.type=='text'))
                assert payload['results'];report['search_ok']=True
                result=await session.call_tool('read_pdf_page',{'attachment_key':record['attachment_key'],'page':record['page']})
                assert not result.isError;report['page_ok']=True
                result=await session.call_tool('view_pdf_page',{'attachment_key':record['attachment_key'],'page':record['page']})
                assert not result.isError and any(c.type=='image' for c in result.content);report['image_ok']=True
            write_json(DATA/'validation/mcp.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(check())
