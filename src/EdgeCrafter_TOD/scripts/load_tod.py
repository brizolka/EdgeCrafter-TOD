#!/usr/bin/env python3

import os
import sys
import zipfile
import logging
import subprocess
from pathlib import Path

DATASET = "ngtininh/ai-tod-v2"

OUTPUT_DIR = Path("./AI-TOD-v2").resolve()
ARCHIVE_DIR = OUTPUT_DIR / "archives"
DATA_DIR = OUTPUT_DIR / "data"

KEEP_ARCHIVE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger("AI-TOD-v2")


def check_kaggle():
    """Проверяет установку Kaggle CLI и авторизацию."""

    try:
        result = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        log.info("Kaggle CLI: %s", result.stdout.strip())

    except FileNotFoundError:
        log.error(
            "Kaggle CLI не найден. Установи его: pip install kaggle"
        )
        sys.exit(1)

    token = Path.home() / ".kaggle" / "kaggle.json"

    if not token.exists() and not (
        os.getenv("KAGGLE_USERNAME")
        and os.getenv("KAGGLE_KEY")
    ):
        log.error(
            "Не найден токен Kaggle.\n"
            "Сохрани kaggle.json в ~/.kaggle/kaggle.json "
            "или задай KAGGLE_USERNAME и KAGGLE_KEY."
        )
        sys.exit(1)


def download_dataset():
    """Скачивает датасет с Kaggle."""

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Начинаем скачивание датасета %s", DATASET)
    log.info("Директория: %s", ARCHIVE_DIR)

    command = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        DATASET,
        "-p",
        str(ARCHIVE_DIR),
    ]

    # Не используем --unzip: архив сначала сохраняется на диск.
    subprocess.run(command, check=True)

    archives = list(ARCHIVE_DIR.glob("*.zip"))

    if not archives:
        raise RuntimeError(
            f"После скачивания ZIP-архив не найден в {ARCHIVE_DIR}"
        )

    return archives


def extract_archives(archives):
    """Проверяет архивы и распаковывает их."""

    for archive in archives:
        log.info("Проверяем архив: %s", archive.name)

        with zipfile.ZipFile(archive, "r") as zf:
            bad_file = zf.testzip()

            if bad_file is not None:
                raise RuntimeError(
                    f"Архив повреждён: {bad_file}"
                )

            log.info(
                "Архив исправен. Файлов внутри: %d",
                len(zf.infolist()),
            )

            # Защита от выхода путей за пределы директории.
            root = DATA_DIR.resolve()

            for member in zf.infolist():
                target = (DATA_DIR / member.filename).resolve()

                if target != root and root not in target.parents:
                    raise RuntimeError(
                        f"Недопустимый путь в архиве: "
                        f"{member.filename}"
                    )

            log.info("Распаковываем в %s", DATA_DIR)
            zf.extractall(DATA_DIR)

        log.info("Распаковка завершена: %s", archive.name)

        if not KEEP_ARCHIVE:
            archive.unlink()
            log.info("Удалён архив: %s", archive.name)


def report():
    """Выводит сводку по скачанным файлам."""

    files = [p for p in DATA_DIR.rglob("*") if p.is_file()]

    extensions = {}

    for path in files:
        ext = path.suffix.lower() or "[без расширения]"
        extensions[ext] = extensions.get(ext, 0) + 1

    total_size = sum(p.stat().st_size for p in files)

    print("\n" + "=" * 55)
    print("AI-TOD-v2: СКАЧИВАНИЕ ЗАВЕРШЕНО")
    print("=" * 55)
    print(f"Директория: {DATA_DIR}")
    print(f"Количество файлов: {len(files)}")
    print(f"Объём распакованных данных: {total_size / 1024**3:.2f} ГиБ")

    print("\nФайлы по расширениям:")

    for ext, count in sorted(
        extensions.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"  {ext}: {count}")

    print("=" * 55)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    check_kaggle()
    archives = download_dataset()
    extract_archives(archives)
    report()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        log.error(
            "Команда Kaggle завершилась с ошибкой (код %s). "
            "Проверь авторизацию, доступ к датасету и интернет.",
            exc.returncode,
        )
        sys.exit(1)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        log.error("Ошибка: %s", exc)
        sys.exit(1)