#!/usr/bin/env python3
import os
import json
import requests
from typing import Dict, Any

# ID задачи, которую хотим получить
ISSUE_ID = "OPD_IPPM-1012"

# URL и токен берутся из переменных окружения (как в вашем проекте)
YOUTRACK_URL = os.getenv('YOUTRACK_URL')
YOUTRACK_TOKEN = os.getenv('YOUTRACK_TOKEN')

# Проверим, что переменные окружения заданы
if not YOUTRACK_URL or not YOUTRACK_TOKEN:
    print("❌ Ошибка: Не заданы YOUTRACK_URL или YOUTRACK_TOKEN")
    print("Убедитесь, что вы активировали виртуальное окружение и загрузили .env")
    exit(1)

# Формируем URL и параметры запроса
url = f"{YOUTRACK_URL}/api/issues/{ISSUE_ID}"
# Запрашиваем все поля, включая кастомные (так же, как в вашем основном коде)
params = {
    "fields": "id,idReadable,summary,description,created,updated,resolved,"
              "customFields(id,projectCustomField(field(name)),value(name,login,fullName,minutes,text,presentation,id))"
}
headers = {"Authorization": f"Bearer {YOUTRACK_TOKEN}"}

print(f"🔍 Запрашиваю задачу {ISSUE_ID}...")
response = requests.get(url, headers=headers, params=params, timeout=30)

if response.status_code == 200:
    data = response.json()
    print("\n✅ Задача успешно получена. Полный JSON:\n")
    # Выводим красиво отформатированный JSON
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Дополнительно: если вы хотите увидеть только кастомные поля,
    # раскомментируйте следующие строки:
    # print("\n--- Кастомные поля ---")
    # for cf in data.get('customFields', []):
    #     print(json.dumps(cf, indent=2, ensure_ascii=False))
        
else:
    print(f"❌ Ошибка {response.status_code}: {response.text}")