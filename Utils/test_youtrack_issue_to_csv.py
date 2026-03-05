#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from EntryPoint.YouTrackEntryPoint import YouTrackEntryPoint

def main():
    result = YouTrackEntryPoint.bulk_youtrack_issue_to_csv(
        user_stories_file="/tmp/user_stories.csv",
        tasks_file="/tmp/tasks.csv",
        page_size=100,
        project_id="OPD_IPPM"
    )
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()