import os
import time
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.Exceptions import HandleException


@CheckRoles(CheckRoles.ANY)
@StringFieldChecker("base_url")
@StringFieldChecker("token")
@StringFieldChecker("project_id", required=False, not_empty=True)
@StringFieldChecker("output_file", required=True, not_empty=True)
@IntFieldChecker("page_size", required=True, min_value=1, max_value=500)
class FetchIssuesToCsvAction(BaseSimpleAction):

    def _extract_flat_row(self, issue: Dict) -> Dict:
        row = {
            "id": issue.get("id"),
            "idReadable": issue.get("idReadable"),
            "summary": issue.get("summary"),
            "description": issue.get("description"),
            "created": issue.get("created"),
            "updated": issue.get("updated"),
            "resolved": issue.get("resolved"),
        }

        for cf in issue.get("customFields", []):
            field_name = cf.get("projectCustomField", {}).get("field", {}).get("name")
            if not field_name:
                continue

            value_obj = cf.get("value")
            if isinstance(value_obj, dict):
                if "name" in value_obj:
                    value = value_obj["name"]
                elif "login" in value_obj:
                    value = value_obj["login"]
                elif "fullName" in value_obj:
                    value = value_obj["fullName"]
                elif "minutes" in value_obj:
                    value = value_obj["minutes"]
                elif "presentation" in value_obj:
                    value = value_obj["presentation"]
                else:
                    value = str(value_obj)
            else:
                value = value_obj

            row[field_name] = value

        return row

    def _write_page_to_csv(self, page_issues: List[Dict], filepath: str, first_page: bool):
        if not page_issues:
            return

        rows = [self._extract_flat_row(issue) for issue in page_issues]
        df = pd.DataFrame(rows)

        mode = 'w' if first_page else 'a'
        header = first_page
        df.to_csv(filepath, mode=mode, header=header, index=False, encoding='utf-8-sig')

    def _handleAspect(self, ctx: Context, params: Dict[str, Any]) -> None:
        base_url = params["base_url"]
        token = params["token"]
        project_id = params.get("project_id")
        output_file = params["output_file"]
        page_size = params["page_size"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        fields = (
            "id,idReadable,summary,description,created,updated,resolved,"
            "customFields(id,projectCustomField(field(name)),value(name,login,fullName,minutes,text,presentation))"
        )

        query = f'project: {project_id}' if project_id else ''
        skip = 0
        first_page = True
        total = 0

        while True:
            req_params = {
                "fields": fields,
                "$top": page_size,
                "$skip": skip
            }
            if query:
                req_params["query"] = query

            try:
                response = requests.get(
                    f"{base_url}/api/issues",
                    headers=headers,
                    params=req_params,
                    timeout=30
                )
            except requests.exceptions.RequestException as e:
                raise HandleException(f"Ошибка соединения: {e}")

            if response.status_code != 200:
                raise HandleException(f"HTTP {response.status_code}: {response.text}")

            issues = response.json()
            if not isinstance(issues, list):
                raise HandleException("Некорректный формат ответа: ожидался список")

            count = len(issues)
            if count == 0:
                break

            self._write_page_to_csv(issues, output_file, first_page)
            first_page = False
            total += count
            print(f"✅ Загружено и сохранено {total} задач...")

            if count < page_size:
                break
            skip += page_size
            time.sleep(0.2)

        print(f"🎉 Всего сохранено {total} задач в {output_file}")
        self._result = {"count": total, "output_file": output_file}