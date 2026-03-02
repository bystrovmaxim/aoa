import os
import json
import requests
from pprint import pprint

# ID интересующей задачи (замените на нужный)
ISSUE_ID = "OPD_IPPM-945"

# Формируем URL и параметры запроса
url = f"{os.getenv('YOUTRACK_URL')}/api/issues/{ISSUE_ID}"
params = {
    "fields": "id,idReadable,summary,description,created,updated,resolved,"
              "customFields(id,projectCustomField(field(name)),value(name,login,fullName,minutes,text,presentation,id))"
}
headers = {"Authorization": f"Bearer {os.getenv('YOUTRACK_TOKEN')}"}

print(f"🔍 Запрашиваю задачу {ISSUE_ID}...")
response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print("\n✅ Задача успешно получена. Содержимое:\n")
    # Выводим общую информацию
    print(f"ID: {data.get('id')}")
    print(f"Readable ID: {data.get('idReadable')}")
    print(f"Summary: {data.get('summary')}")
    print(f"Description: {data.get('description')}")
    print(f"Created: {data.get('created')}")
    print(f"Updated: {data.get('updated')}")
    print(f"Resolved: {data.get('resolved')}")

    # Выводим кастомные поля
    print("\n📋 Кастомные поля:")
    for cf in data.get('customFields', []):
        field_name = cf.get('projectCustomField', {}).get('field', {}).get('name')
        value_obj = cf.get('value')
        # Пытаемся извлечь читаемое значение
        if isinstance(value_obj, dict):
            if 'name' in value_obj:
                value = value_obj['name']
            elif 'login' in value_obj:
                value = value_obj['login']
            elif 'fullName' in value_obj:
                value = value_obj['fullName']
            elif 'minutes' in value_obj:
                value = value_obj['minutes']
            elif 'presentation' in value_obj:
                value = value_obj['presentation']
            else:
                value = str(value_obj)
        else:
            value = value_obj
        print(f"  - {field_name}: {value}")

    # Полный вывод в JSON для детального анализа (раскомментируйте при необходимости)
    # print("\n📦 Полный JSON:")
    # print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"❌ Ошибка {response.status_code}: {response.text}")