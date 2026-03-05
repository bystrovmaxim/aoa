#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

from MCPServer.YouTrackMCPServer import YouTrackMCPServer

def main():
    result = YouTrackMCPServer.init_database()
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()