import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from agent.graph import build_agent_graph

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/mcp_server.py"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            graph = await build_agent_graph(session)

            while True:
                user = input("User: ")
                if not user:
                    break
                result = await graph.ainvoke({"messages": [{"role": "user", "content": user}]})
                print("AI:", result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())