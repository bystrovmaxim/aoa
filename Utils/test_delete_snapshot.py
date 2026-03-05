#!/usr/bin/env python3
import sys
import os
import json
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from MCPServer.YouTrackMCPServer import YouTrackMCPServer

def main():
    result = YouTrackMCPServer.delete_snapshot(
        snapshot_date=date.today(),
        tables=["user_tech_stories", "taskitems"],
        schema="youtrack"
    )
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()