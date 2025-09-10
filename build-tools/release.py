# release.py — выпуск новой версии

import subprocess
import sys
from pathlib import Path


def run(cmd: str, check=True, shell=True):
    """Выполняет команду с безопасным чтением вывода"""
    print(f"🔧 Выполняю: {cmd}")
    result = subprocess.run(
        cmd,
        shell=shell,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    if result.stdout:
        clean_out = result.stdout.strip()
        if clean_out:
            print(f"✅ {clean_out}")
    if result.stderr:
        clean_err = result.stderr.strip()
        if clean_err:
            print(f"⚠️  {clean_err}")
    if check and result.returncode != 0:
        print(f"❌ Ошибка выполнения команды: {result.returncode}")
        sys.exit(result.returncode)
    return result


# === Определяем пути ===
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name == 'build-tools' else SCRIPT_DIR
VERSION_FILE = ROOT_DIR / "VERSION"


# === Основная логика ===
def main():
    print("🚀 Скрипт выпуска новой версии")
    print("Формат версии: X.Y.Z, например: 1.5.0")

    version = input("\nВведите номер версии: ").strip()

    # Проверка формата
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        print("❌ Ошибка: версия должна быть в формате X.Y.Z (например, 1.5.0)")
        sys.exit(1)

    tag_name = f"v{version}"

    print(f"\n📦 Версия: {version}")
    print(f"🏷  Тег: {tag_name}")

    confirm = input("\nПодтвердите выпуск (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("❌ Отменено пользователем")
        sys.exit(0)

    # Обновляем VERSION
    try:
        with open(VERSION_FILE, "w", encoding="utf-8", newline='\n') as f:
            f.write(f"{version}\n")
        print(f"✅ Записано в VERSION: {version}")
    except Exception as e:
        print(f"❌ Не удалось записать VERSION: {e}")
        sys.exit(1)

    # Git команды
    run("git add VERSION")
    run(f'git commit -m "chore: bump version to {version}"')
    run("git checkout main")

    # Merge (не критичен)
    merge_result = run(
        "git merge HEAD@{1} --no-ff -m 'chore: merge release branch'", check=False)
    if merge_result.returncode != 0:
        print("ℹ️  Merge не требуется или уже выполнен")

    run("git push origin main")
    run(f"git tag {tag_name}")
    run(f"git push origin {tag_name}")

    print("\n" + "✅" * 50)
    print(f"🎉 Выпуск {tag_name} запущен!")
    print("Запустите сборку вручную или настройте GitHub Actions:")
    print("  python build.py")
    print("✅" * 50)


if __name__ == "__main__":
    main()
