#!/usr/bin/env python3
import sys
import os
import json
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from Gateway.YouTrackMCPServer import YouTrackMCPServer

def main():
    result = YouTrackMCPServer.bulk_youtrack_issue_to_postgres(
        page_size=5000,
        snapshot_date=date.today()
    )
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()