import os
import asyncio
from typing import List, Annotated, TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import tools_condition, ToolNode

from langchain_mcp_adapters.tools import load_mcp_tools
# No prompts/resources in the new server, so we drop these:
# from langchain_mcp_adapters.resources import load_mcp_resources
# from langchain_mcp_adapters.prompts import load_mcp_prompt

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]

async def build_agent_graph(session: ClientSession):
    # 1) Base LLM
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)

    # 2) Load only MCP tools (greet + GitHub tools) from the new server
    tools = await load_mcp_tools(session)

    # 3) Bind tools to the model
    llm_with_tools = llm.bind_tools(tools)

    # 4) Prompt template (default system + conversation)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use tools when they are relevant."),
        MessagesPlaceholder("messages"),
    ])

    chain = prompt | llm_with_tools

    # 5) Node that runs the model (async)
    async def chat_node(state: AgentState) -> AgentState:
        ai_msg = await chain.ainvoke({"messages": state["messages"]})
        return {"messages": state["messages"] + [ai_msg]}

    # 6) Build graph
    builder = StateGraph(AgentState)
    builder.add_node("chat", chat_node)
    builder.add_node("tools", ToolNode(tools=tools))

    builder.add_edge(START, "chat")
    builder.add_conditional_edges("chat", tools_condition, {"tools": "tools", "__end__": END})
    builder.add_edge("tools", "chat")

    return builder.compile()

async def run_once(user_text: str) -> str:
    """Convenience: spin up stdio MCP server, build agent, answer once."""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/mcp_server.py"],  # <- path to your updated MCP server
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            graph = await build_agent_graph(session)
            state = {"messages": [{"role": "user", "content": user_text}]}
            result = await graph.ainvoke(state)
            # messages[-1].content can be a str or a list of content parts in some runtimes
            last = result["messages"][-1].content
            if isinstance(last, list):
                # join any text parts if needed
                return "".join(getattr(p, "text", str(p)) for p in last)
            return last

if __name__ == "__main__":
    print(asyncio.run(run_once("List open issues in rohit3773/mcp_github_tools")))
