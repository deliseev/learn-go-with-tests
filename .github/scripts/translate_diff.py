import os
import re
import subprocess
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

# Инициализируем клиента
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"
GIT_TIMEOUT_SECONDS = 30
COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
# Совпадает по шаблону с .github/upstream-sync-state.txt (sync-upstream.yml) —
# оба маркера отвечают на вопрос "до какого коммита апстрима синкнулись".
STATE_FILE = ".github/translate-sync-state.txt"
UPSTREAM_STATE_FILE = ".github/upstream-sync-state.txt"

def translate_content(content):
    prompt = f"""
    You are a professional technical translator specializing in Go (Golang).
    Translate the following Markdown document into Russian.

    Strict rules:
    1. Keep all Markdown syntax intact (headers, lists, bold text, links).
    2. Do NOT translate or modify Go code blocks (```go ... ```), inline code (e.g. `t.Run`), variable names, and function names.
    3. Keep links format [text](url) intact, but you can translate the link text if appropriate.
    4. Use standard Russian Go terminology (e.g., "срез" for slice, "указатель" for pointer, "структура" for struct).

    Document to translate:
    ---
    {content}
    ---
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text

def is_excluded_path(path):
    parts = path.split("/")
    return ".github" in parts or "node_modules" in parts

def main():
    if not os.path.exists(STATE_FILE):
        print(f"Error: {STATE_FILE} not found. Creating a baseline from origin/main.")
        # Если файла нет, мы не можем выявить разницу. Запишем текущий коммит.
        try:
            current_commit = subprocess.check_output(
                ["git", "rev-parse", "origin/main"], text=True, timeout=GIT_TIMEOUT_SECONDS
            ).strip()
            with open(STATE_FILE, "w") as f:
                f.write(current_commit)
        except Exception as e:
            print(f"Error initializing baseline: {e}")
            exit(1)
        return

    with open(STATE_FILE, "r") as f:
        last_commit = f.read().strip()

    if not COMMIT_SHA_RE.match(last_commit):
        print(f"Error: {STATE_FILE} contains an invalid commit SHA: {last_commit!r}")
        exit(1)

    # Получаем последний коммит из обновленной ветки main на GitHub
    try:
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "origin/main"], text=True, timeout=GIT_TIMEOUT_SECONDS
        ).strip()
    except Exception as e:
        print(f"Error getting origin/main commit: {e}")
        exit(1)

    # Сверка с независимым маркером sync-upstream.yml — просто предупреждение,
    # не блокирует перевод. Расхождение обычно значит, что один из маркеров
    # откатили вручную, не тронув другой.
    try:
        upstream_marker = subprocess.check_output(
            ["git", "show", f"origin/main:{UPSTREAM_STATE_FILE}"], text=True, timeout=GIT_TIMEOUT_SECONDS
        ).strip()
        if upstream_marker != current_commit:
            print(
                f"Warning: {UPSTREAM_STATE_FILE} on main ({upstream_marker}) does not match "
                f"origin/main HEAD ({current_commit}) — the two sync markers may have drifted "
                "apart (e.g. after a manual reset of one of them). Continuing anyway."
            )
    except Exception:
        pass  # informational only — a missing/unreadable marker shouldn't block translation

    if last_commit == current_commit:
        print("Everything is up to date. No new commits in main.")
        return

    print(f"Detecting changes between {last_commit} and {current_commit}...")

    try:
        # Находим измененные, добавленные и удаленные (.md) файлы
        diff_lines = subprocess.check_output(
            ["git", "diff", "--name-status", "--diff-filter=AMD", last_commit, "origin/main", "--", "*.md"],
            text=True, timeout=GIT_TIMEOUT_SECONDS
        ).splitlines()
    except Exception as e:
        print(f"Error running git diff: {e}")
        exit(1)

    # Список исключений
    black_list = ["readme.md", "gb-readme.md", "license.md", "contributing.md", "code_of_conduct.md"]
    files_to_translate = []
    files_to_remove = []
    for line in diff_lines:
        status, path = line.split("\t", 1)
        filename = os.path.basename(path).lower()
        if is_excluded_path(path) or filename in black_list:
            continue
        if status == "D":
            files_to_remove.append(path)
        else:
            files_to_translate.append(path)

    had_failures = False

    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed translation for upstream-deleted file: {file_path}")
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
            had_failures = True

    if not files_to_translate and not files_to_remove:
        print("No content-related markdown files were updated in this sync.")
        # Обновляем коммит, чтобы не проверять эти изменения снова
        with open(STATE_FILE, "w") as f:
            f.write(current_commit)
        return

    print(f"Found {len(files_to_translate)} files to translate.")
    for file_path in files_to_translate:
        print(f"Translating updated English file from main: {file_path}")

        # Загружаем новое английское содержимое файла из ветки main
        try:
            english_content = subprocess.check_output(
                ["git", "show", f"origin/main:{file_path}"], text=True, timeout=GIT_TIMEOUT_SECONDS
            )
        except Exception as e:
            print(f"Error reading {file_path} from main: {e}")
            had_failures = True
            continue

        # Переводим его
        try:
            russian_translation = translate_content(english_content)
            if not russian_translation or not russian_translation.strip():
                raise ValueError("translation API returned an empty response")

            # Сохраняем перевод в текущую рабочую директорию (ветка ru)
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(russian_translation)
            print(f"Successfully updated and translated: {file_path}")
        except Exception as e:
            print(f"Error translating content for {file_path}: {e}")
            had_failures = True

    if had_failures:
        print(f"One or more files failed; not advancing {STATE_FILE} so they are retried next run.")
        exit(1)

    # Обновляем маркер последнего синхронизированного коммита
    with open(STATE_FILE, "w") as f:
        f.write(current_commit)

if __name__ == "__main__":
    main()
