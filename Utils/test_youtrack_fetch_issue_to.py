#!/usr/bin/env python3
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

ISSUE_ID = "OPD_IPPM-1012"

YOUTRACK_URL = os.getenv('YOUTRACK_URL')
YOUTRACK_TOKEN = os.getenv('YOUTRACK_TOKEN')

if not YOUTRACK_URL or not YOUTRACK_TOKEN:
    print(json.dumps({"error": "YOUTRACK_URL или YOUTRACK_TOKEN не заданы"}))
    exit(1)

url = f"{YOUTRACK_URL}/api/issues/{ISSUE_ID}"
params = {
    "fields": (
        "id,idReadable,summary,description,created,updated,resolved,"
        "customFields(id,projectCustomField(field(name)),value(name,login,fullName,minutes,text,presentation,id)),"
        "parent(idReadable,summary),"
        "subtasks(idReadable,summary),"
        "links(direction,linkType(name),issues(idReadable,summary)),"
        "comments(id,text,author(id,login,fullName),created),"
        "attachments(id,name,url)"
    )
}
headers = {"Authorization": f"Bearer {YOUTRACK_TOKEN}"}

print(f"🔍 Запрашиваю задачу {ISSUE_ID} и все связанные элементы...")
response = requests.get(url, headers=headers, params=params, timeout=30)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(json.dumps({"error": f"HTTP {response.status_code}", "details": response.text}))