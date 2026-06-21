import os
import subprocess
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

# Инициализируем клиента
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

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

def main():
    if not os.path.exists(".last_synced_commit"):
        print("Error: .last_synced_commit not found. Creating a baseline from origin/main.")
        # Если файла нет, мы не можем выявить разницу. Запишем текущий коммит.
        try:
            current_commit = subprocess.check_output(
                ["git", "rev-parse", "origin/main"], text=True
            ).strip()
            with open(".last_synced_commit", "w") as f:
                f.write(current_commit)
        except Exception as e:
            print(f"Error initializing baseline: {e}")
        return

    with open(".last_synced_commit", "r") as f:
        last_commit = f.read().strip()

    # Получаем последний коммит из обновленной ветки main на GitHub
    try:
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "origin/main"], text=True
        ).strip()
    except Exception as e:
        print(f"Error getting origin/main commit: {e}")
        return

    if last_commit == current_commit:
        print("Everything is up to date. No new commits in main.")
        return

    print(f"Detecting changes between {last_commit} and {current_commit}...")

    try:
        # Находим только измененные или добавленные (.md) файлы
        files = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=AM", last_commit, "origin/main", "--", "*.md"],
            text=True
        ).splitlines()
    except Exception as e:
        print(f"Error running git diff: {e}")
        return

    # Список исключений
    black_list = ["readme.md", "license.md", "contributing.md", "code_of_conduct.md"]
    files_to_translate = []
    for f in files:
        filename = os.path.basename(f).lower()
        if ".github" not in f and "node_modules" not in f and filename not in black_list:
            files_to_translate.append(f)

    if not files_to_translate:
        print("No content-related markdown files were updated in this sync.")
        # Обновляем коммит, чтобы не проверять эти изменения снова
        with open(".last_synced_commit", "w") as f:
            f.write(current_commit)
        return

    print(f"Found {len(files_to_translate)} files to translate.")
    for file_path in files_to_translate:
        print(f"Translating updated English file from main: {file_path}")

        # Загружаем новое английское содержимое файла из ветки main
        try:
            english_content = subprocess.check_output(
                ["git", "show", f"origin/main:{file_path}"], text=True
            )
        except Exception as e:
            print(f"Error reading {file_path} from main: {e}")
            continue

        # Переводим его
        try:
            russian_translation = translate_content(english_content)

            # Сохраняем перевод в текущую рабочую директорию (ветка ru)
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(russian_translation)
            print(f"Successfully updated and translated: {file_path}")
        except Exception as e:
            print(f"Error translating content for {file_path}: {e}")

    # Обновляем маркер последнего синхронизированного коммита
    with open(".last_synced_commit", "w") as f:
        f.write(current_commit)

if __name__ == "__main__":
    main()
