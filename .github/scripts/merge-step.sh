#!/usr/bin/env bash
# Мержит одну ветку в другую и пушит результат.
#
# Синхронизация форка устроена цепочкой мержей:
#
#   upstream/main → main-upstream → main-ru → ru
#
# Каждое звено — обычный git merge, поэтому удаления, переименования и
# трёхсторонние слияния достаются от git бесплатно, а база хранится в графе
# коммитов, а не в текстовом маркере, который может молча уехать вперёд.
#
# При конфликте работа не бросается: состояние мержа уезжает в отдельную ветку
# и на неё открывается PR. Разрешать конфликт в вебе дешевле, чем
# воспроизводить его у себя руками.
#
# Использование: merge-step.sh <ветка-приёмник> <ссылка-источник>
set -euo pipefail

TARGET=${1:?не указана ветка-приёмник}
SOURCE=${2:?не указана ссылка-источник}

git checkout "$TARGET"

# Перевод никогда не сливается с оригиналом построчно: git взял бы английские
# куски и вставил их в русский текст. За это отвечает атрибут `*.md merge=ours`
# в .gitattributes ветки ru — но атрибут без одноимённого драйвера git не
# применит. Проверяем оба до мержа: упасть здесь дешевле, чем разбирать потом
# главу с английскими вставками.
if [ -f .gitattributes ] && grep -q '^\*\.md merge=ours' .gitattributes; then
  if [ "$(git config --get merge.ours.driver || true)" != "true" ]; then
    echo "::error::merge.ours.driver не настроен — запусти 'git config merge.ours.driver true'"
    exit 1
  fi
  # Пути намеренно синтетические: git check-attr сопоставляет шаблоны, файл
  # существовать не обязан. Реальное имя главы здесь стало бы миной — стоило бы
  # апстриму её переименовать, и проверка начала бы валить мерж на ровном месте.
  if ! git check-attr merge -- __merge_guard__.md | grep -q ': merge: ours$'; then
    echo "::error::атрибут merge=ours не действует на *.md — проверь .gitattributes"
    exit 1
  fi
  # Документация самого тулинга живёт на main-ru и должна доезжать сюда,
  # поэтому под merge=ours она попадать не должна.
  if git check-attr merge -- .github/scripts/__merge_guard__.md | grep -q ': merge: ours$'; then
    echo "::error::merge=ours не должен действовать на .github/**/*.md"
    exit 1
  fi
fi

if git merge --no-edit "$SOURCE"; then
  git push origin "HEAD:$TARGET"
  echo "Смержено: $SOURCE → $TARGET"
  exit 0
fi

BRANCH="sync/conflict-${TARGET}-$(date -u +%Y%m%d-%H%M%S)"
echo "Конфликт при мерже $SOURCE → $TARGET, уношу состояние в $BRANCH"

# Конфликтные файлы коммитятся вместе с маркерами: `git add` снимает с них
# отметку unmerged, и коммит проходит. Смысл в том, чтобы работа мержа не
# пропала — разрешать её будет человек в PR.
git add -A
git commit -m "chore: конфликт при мерже $SOURCE в $TARGET"
git push origin "HEAD:$BRANCH"

gh pr create \
  --base "$TARGET" \
  --head "$BRANCH" \
  --title "Конфликт синхронизации: $SOURCE → $TARGET" \
  --body "$(cat <<BODY
Автоматический мерж \`$SOURCE\` → \`$TARGET\` упёрся в конфликт. Состояние
мержа закоммичено **вместе с маркерами конфликта**, чтобы работа не пропала.

Разреши конфликты в этой ветке и смержи PR. До тех пор синхронизация
дальше по цепочке не пойдёт.

Файлы с маркерами:

\`\`\`
$(git grep -l '^<<<<<<< ' -- . || echo '(не найдены — проверь дифф вручную)')
\`\`\`
BODY
)"

exit 1
