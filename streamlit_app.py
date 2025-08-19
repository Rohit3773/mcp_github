import os
import asyncio
import streamlit as st
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent.graph import build_agent_graph

load_dotenv()

st.set_page_config(page_title="MCP + LangGraph Chat", page_icon="🧩")
st.title("🧩 MCP Server × LangGraph × Streamlit")

if "history" not in st.session_state:
    st.session_state.history = []  # list of (role, content)

user_input = st.chat_input("Ask me anything… (I can call MCP tools)")

async def answer_with_agent(user_text: str) -> str:
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/mcp_server.py"],
        env=None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            graph = await build_agent_graph(session)
            result = await graph.ainvoke({"messages": [{"role": "user", "content": user_text}]})
            return result["messages"][-1].content

# Render history
for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

if user_input:
    st.session_state.history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("Thinking…")
        try:
            reply = asyncio.run(answer_with_agent(user_input))
        except RuntimeError:
            # Fallback for nested event loop (e.g., in some environments)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            reply = loop.run_until_complete(answer_with_agent(user_input))
            loop.close()
        msg_placeholder.markdown(reply)
        st.session_state.history.append(("assistant", reply))

if __name__ == '__main__':
    pass