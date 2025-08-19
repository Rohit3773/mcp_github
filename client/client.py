import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Update the path below to your server file if different
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server/mcp_server.py"],
    env=None,
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ---- Tools ----
            response = await session.list_tools()
            print("\n// tools //")
            for t in response.tools:
                print(f"- {t.name}")

            # ---- greet ----
            result = await session.call_tool("greet", arguments={"name": "Rohit"})
            print("\n// greet //")
            print(result.content[0].text)

            # ---- list open issues ----
            result = await session.call_tool(
                "gh_list_open_issues",
                arguments={
                    "owner": "rohit3773",
                    "repo": "mcp_github_tools",
                    # Optional filters:
                    # "labels": ["bug", "ui"],
                    # "assignee": "*",
                    "limit": 10,
                },
            )
            print("\n// gh_list_open_issues //")
            print(result.content[0].text)

            # ---- create issue (requires GITHUB_TOKEN in server .env) ----
            result = await session.call_tool(
                "gh_create_issue",
                arguments={
                    "owner": "rohit3773",
                    "repo": "mcp_github_tools",
                    "title": "Login button misaligned",
                    "body": "Repro: open home page on iPhone 14…",
                    "labels": ["ui", "bug"],
                },
            )
            print("\n// gh_create_issue //")
            print(result.content[0].text)

            # ---- open pull request (optional example) ----
            # result = await session.call_tool(
            #     "gh_open_pull_request",
            #     arguments={
            #         "owner": "rohit3773",
            #         "repo": "mcp_github_tools",
            #         "head": "feature/login-fix",
            #         "base": "main",
            #         "title": "Fix login button alignment",
            #         "body": "This PR fixes the misaligned login button on iPhone 14.",
            #         "draft": False,
            #         "maintainer_can_modify": True,
            #     },
            # )
            # print("\n// gh_open_pull_request //")
            # print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
