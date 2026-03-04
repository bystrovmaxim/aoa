#!/usr/bin/env python3
import os
import json
import requests

# ID задачи
ISSUE_ID = "OPD_IPPM-1012"

# Переменные окружения
YOUTRACK_URL = os.getenv('YOUTRACK_URL')
YOUTRACK_TOKEN = os.getenv('YOUTRACK_TOKEN')

if not YOUTRACK_URL or not YOUTRACK_TOKEN:
    print("❌ Ошибка: Не заданы YOUTRACK_URL или YOUTRACK_TOKEN")
    exit(1)

# Запрос с максимально полным набором связанных данных
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
    print("\n✅ Задача успешно получена. Полный JSON:\n")
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"❌ Ошибка {response.status_code}: {response.text}")