import os
import requests
from typing import Dict, Any

# Настройки
YOUTRACK_URL = os.getenv('YOUTRACK_URL')
TOKEN = os.getenv('YOUTRACK_TOKEN')
FIELD_NAME = '_Тип карточки'

# Заголовки для API
headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

def get_projects() -> list:
    """Получить список проектов (ограничимся несколькими)"""
    url = f'{YOUTRACK_URL}/api/admin/projects'
    params = {
        'fields': 'id,name,customFields(id,field(name),bundle(id,name))',
        '$top': 10
    }
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def find_field_in_projects(projects: list, field_name: str) -> Dict[str, Any]:
    """Ищет кастомное поле с заданным именем во всех проектах, возвращает информацию о нём и бандле"""
    for proj in projects:
        for cf in proj.get('customFields', []):
            if cf.get('field', {}).get('name') == field_name:
                bundle = cf.get('bundle')
                if bundle:
                    return {
                        'project_id': proj['id'],
                        'project_name': proj['name'],
                        'field_id': cf['id'],
                        'bundle_id': bundle['id'],
                        'bundle_name': bundle.get('name')
                    }
    return None

def get_enum_bundle(bundle_id: str) -> list:
    """Получает все значения enum-бандла по его ID"""
    url = f'{YOUTRACK_URL}/api/admin/customFieldSettings/bundles/enum/{bundle_id}/values'
    params = {
        'fields': 'id,name,ordinal,description,color(id)',
        '$top': 100
    }
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def main():
    print(f"🔍 Ищем поле '{FIELD_NAME}' в проектах...")
    projects = get_projects()
    field_info = find_field_in_projects(projects, FIELD_NAME)

    if not field_info:
        print(f"❌ Поле '{FIELD_NAME}' не найдено в первых {len(projects)} проектах.")
        print("Возможно, оно находится в другом проекте. Попробуйте расширить список проектов.")
        return

    print(f"✅ Поле найдено в проекте: {field_info['project_name']}")
    print(f"   ID бандла: {field_info['bundle_id']}")
    print(f"   Имя бандла: {field_info.get('bundle_name', 'не указано')}")

    print("\n📋 Запрашиваю возможные значения...")
    values = get_enum_bundle(field_info['bundle_id'])

    if not values:
        print("⚠️  Бандл не содержит значений (или пуст).")
    else:
        print(f"Найдено {len(values)} значений:")
        for val in values:
            print(f"  - {val.get('name')} (id: {val.get('id')})")

if __name__ == '__main__':
    main()