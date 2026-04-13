#!/usr/bin/env bash
# Два шага: новая ветка → правки вручную → add/commit/push + ссылка на PR (после Create PR запускается CI).
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Запускай из git-репозитория."
  exit 1
}
cd "$ROOT"

github_compare_url() {
  local remote raw owner_repo
  remote="$(git remote get-url origin 2>/dev/null || true)"
  raw="${remote%.git}"
  if [[ "$raw" =~ github\.com[:/](.+/.+)$ ]]; then
    owner_repo="${BASH_REMATCH[1]//:/\/}"
  else
    echo ""
    return 1
  fi
  local branch
  branch="$(git branch --show-current)"
  echo "https://github.com/${owner_repo}/compare/main...${branch}?expand=1"
}

cmd_new() {
  local name="${1:-}"
  if [[ -z "$name" ]]; then
    echo "Использование: $0 new <имя-ветки>"
    exit 1
  fi
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Рабочее дерево не чистое. Закоммить или убери изменения, потом снова: $0 new ..."
    exit 1
  fi
  git fetch origin
  git checkout main
  git pull --ff-only origin main
  git checkout -b "$name"
  echo "Ветка «$name» от актуального main. Вноси изменения, затем:"
  echo "  $0 ship \"краткое сообщение коммита\""
}

cmd_ship() {
  local msg="${1:-}"
  if [[ -z "$msg" ]]; then
    echo "Использование: $0 ship \"сообщение коммита\""
    exit 1
  fi
  local branch
  branch="$(git branch --show-current)"
  if [[ "$branch" == "main" ]]; then
    echo "Сейчас ветка main. Сначала: $0 new <ветка>"
    exit 1
  fi
  git add -A
  if git diff --cached --quiet; then
    echo "Нечего коммитить (после git add пусто). Сделай правки или проверь git status."
    exit 1
  fi
  git commit -m "$msg"
  git push -u origin HEAD
  local url
  url="$(github_compare_url)" || {
    echo "Не удалось разобрать origin (нужен github.com). Запушено: origin/$branch"
    exit 0
  }
  echo ""
  echo "Пуш выполнен. Чтобы запустился workflow CI, на GitHub создай PR в main:"
  echo "  $url"
  echo ""
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "$url" || true
  fi
}

case "${1:-}" in
  new) shift; cmd_new "$@" ;;
  ship) shift; cmd_ship "$@" ;;
  *)
    echo "Использование:"
    echo "  $0 new <имя-ветки>     — ветка от обновлённого main"
    echo "  $0 ship \"сообщение\"  — git add -A, commit, push, ссылка на создание PR"
    exit 1
    ;;
esac
