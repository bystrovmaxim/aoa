#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from YouTrackMCP import YouTrackMCPServer

if __name__ == "__main__":
    result = YouTrackMCPServer.init_database()
    print(result)