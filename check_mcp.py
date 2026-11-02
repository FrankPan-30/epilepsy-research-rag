"""Exercise actual stdio MCP transport and evidence tools end to end."""
import asyncio,json,os,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from rag import ROOT,DATA,write_json,stamp

async def check():
    params=StdioServerParameters(command=str(ROOT/'.venv/bin/python'),args=[str(ROOT/'mcp_server.py')],env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
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
                result=await session.call_tool('search_literature',{'query':'PAPC 功率谱参数化 自适应通道选择','limit':5})
                assert not result.isError;report['search_ok']=True
                result=await session.call_tool('view_pdf_page',{'attachment_key':'LC7RUHV3','page':3})
                assert not result.isError and any(c.type=='image' for c in result.content);report['image_ok']=True
            write_json(DATA/'validation/mcp.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(check())
