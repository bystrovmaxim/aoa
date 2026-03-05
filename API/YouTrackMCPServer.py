import asyncio
import json
import logging
from typing import Any, Dict
import sys

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Импортируем фасад из Gateway
from EntryPoint.YouTrackMCPServer import YouTrackMCPServer as Facade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-youtrack")

server = Server("youtrack-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="bulk_youtrack_issue_to_csv",
            description="Export YouTrack issues to CSV files. Fetches all issues from a specified project and saves them into two CSV files: one for user/tech stories, another for tasks. Returns total issues count and pages processed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_stories_file": {
                        "type": "string",
                        "description": "Path where the CSV file for stories (User stories, Technical stories) will be saved. Example: '/tmp/user_stories.csv'"
                    },
                    "tasks_file": {
                        "type": "string",
                        "description": "Path where the CSV file for tasks (Development, Analytics, Incidents, Work instead of system) will be saved. Example: '/tmp/tasks.csv'"
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 100,
                        "description": "Number of issues per page (1-500). Larger pages reduce number of requests but may time out."
                    },
                    "project_id": {
                        "type": "string",
                        "description": "YouTrack project ID to export (e.g., 'OPD_IPPM'). If omitted, exports all accessible issues."
                    }
                }
            }
        ),
        types.Tool(
            name="bulk_youtrack_issue_to_postgres",
            description="Load YouTrack issues as daily snapshots into PostgreSQL. For each issue, stores its state at the given snapshot date. Data is saved into two tables: 'user_tech_stories' and 'taskitems' within the specified schema. Returns total issues count and pages processed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "YouTrack project ID (e.g., 'OPD_IPPM'). If omitted, loads all accessible issues."
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 100,
                        "description": "Number of issues per page (1-500)."
                    },
                    "snapshot_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Snapshot date in YYYY-MM-DD format (e.g., '2025-03-05'). If omitted, uses current date."
                    }
                }
            }
        ),
        types.Tool(
            name="delete_snapshot",
            description="Delete all records for a given snapshot date from specified PostgreSQL tables. Useful for cleaning up data before re-importing. Returns total number of deleted rows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "snapshot_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Snapshot date to delete (YYYY-MM-DD)."
                    },
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of table names to clean. Example: ['user_tech_stories', 'taskitems']"
                    },
                    "schema": {
                        "type": "string",
                        "default": "youtrack",
                        "description": "Database schema where tables reside (default: 'youtrack')."
                    }
                },
                "required": ["snapshot_date", "tables"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    logger.info(f"Calling tool {name} with arguments {arguments}")
    try:
        if name == "bulk_youtrack_issue_to_csv":
            result = Facade.bulk_youtrack_issue_to_csv(
                user_stories_file=arguments.get("user_stories_file"),
                tasks_file=arguments.get("tasks_file"),
                page_size=arguments.get("page_size", 100),
                project_id=arguments.get("project_id")
            )
        elif name == "bulk_youtrack_issue_to_postgres":
            result = Facade.bulk_youtrack_issue_to_postgres(
                project_id=arguments.get("project_id"),
                page_size=arguments.get("page_size", 100),
                snapshot_date=arguments.get("snapshot_date")
            )
        elif name == "delete_snapshot":
            result = Facade.delete_snapshot(
                snapshot_date=arguments["snapshot_date"],
                tables=arguments["tables"],
                schema=arguments.get("schema", "youtrack")
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        text_result = json.dumps(result, ensure_ascii=False)
        return [types.TextContent(type="text", text=text_result)]
    except Exception as e:
        logger.exception(f"Error executing {name}")
        error_text = json.dumps({"error": str(e)}, ensure_ascii=False)
        return [types.TextContent(type="text", text=error_text)]

async def main():
    print("MCP server starting...", file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("MCP server initialized, waiting for requests...", file=sys.stderr)
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="youtrack-mcp-server",
                server_version="1.0.0",
                capabilities={}
            )
        )

if __name__ == "__main__":
    asyncio.run(main())