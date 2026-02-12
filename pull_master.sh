#!/bin/bash
# Обновить репозиторий A2A до актуальной ветки master
set -e
cd "$(dirname "$0")"
echo "→ Репозиторий: $(pwd)"
git fetch origin
git checkout master
git pull origin master
echo "✅ Готово. Ветка master актуальна."
