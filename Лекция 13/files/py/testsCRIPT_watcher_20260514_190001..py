import os
import shutil
import zipfile
import time
from datetime import datetime

# Константы
WATCH_DIR = "files"  # Папка, которую нужно мониторить
SLEEP_TIME = 1       # Время задержки между проверками (в секундах)
ARCHIVE_EXTENSIONS = ('.zip', '.tar')  # Поддерживаемые форматы архивов

# Множество для отслеживания уже обработанных файлов (чтобы не обрабатывать один файл дважды)
processed_files = set()


def get_file_extension(filename):
    """Возвращает расширение файла без точки."""
    _, ext = os.path.splitext(filename)
    return ext.lower().replace('.', '') if ext else 'no_ext'


def generate_new_name(original_filename, is_from_archive=False, archive_name=""):
    """
    Генерирует новое имя файла согласно ТЗ.
    Формат: [имя_архива_]оригинальное_имя_дата.расширение
    """
    name_without_ext, ext = os.path.splitext(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if is_from_archive and archive_name:
        # Если файл из архива: имя_архива_оригинальное_имя_дата.расширение
        new_name = f"{archive_name}_{name_without_ext}_{timestamp}.{ext}"
    else:
        # Если обычный файл (без имени архива): оригинальное_имя_дата.расширение
        new_name = f"{name_without_ext}_{timestamp}.{ext}"

    return new_name


def sort_and_move_file(file_path, is_from_archive=False, archive_name=""):
    """
    Сортирует файл: создает папку по расширению и перемещает туда с новым именем.
    """
    filename = os.path.basename(file_path)
    extension = get_file_extension(filename)

    # Создаем целевую директорию (например, files/txt), если её нет
    target_dir = os.path.join(WATCH_DIR, extension)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"[INFO] Создана новая папка для сортировки: {target_dir}")

    # Генерируем новое имя
    new_filename = generate_new_name(filename, is_from_archive, archive_name)
    
    # Формируем полный путь назначения
    dest_path = os.path.join(target_dir, new_filename)

    try:
        shutil.move(file_path, dest_path)
        print(f"[SUCCESS] Перемещен файл: {filename} -> {new_filename}")
    except Exception as e:
        print(f"[ERROR] Ошибка при перемещении файла {filename}: {e}")


def process_archive(archive_path):
    """
    Распаковывает архив, сортирует содержимое и удаляет исходный архив.
    """
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    print(f"[INFO] Обнаружен архив: {os.path.basename(archive_path)}. Начинаю распаковку...")

    # Создаем временную папку для распаковки внутри WATCH_DIR
    temp_extract_dir = os.path.join(WATCH_DIR, "temp_unpack", archive_name)
    if not os.path.exists(temp_extract_dir):
        os.makedirs(temp_extract_dir)

    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # Распаковываем все файлы во временную папку
            zip_ref.extractall(temp_extract_dir)
        
        print(f"[INFO] Архив {os.path.basename(archive_path)} успешно распакован.")

        # Проходим по всем файлам внутри распакованной директории
        for root, dirs, files in os.walk(temp_extract_dir):
            for file_name in files:
                full_file_path = os.path.join(root, file_name)
                
                # Сортируем каждый файл из архива
                sort_and_move_file(full_file_path, is_from_archive=True, archive_name=archive_name)

        print(f"[INFO] Удаление временных файлов и исходного архива...")
        
        # Удаляем распакованные файлы (они уже перемещены)
        shutil.rmtree(temp_extract_dir)
        # Удаляем сам архив из папки мониторинга
        os.remove(archive_path)
        print(f"[SUCCESS] Исходный архив {os.path.basename(archive_path)} удален.")

    except zipfile.BadZipFile:
        print(f"[ERROR] Файл {archive_path} не является корректным ZIP-архивом.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке архива {archive_path}: {e}")


def main():
    """Основной цикл мониторинга."""
    # Создаем папку для мониторинга, если её нет
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
        print(f"[INFO] Папка '{WATCH_DIR}' создана.")

    print(f"--- Скрипт мониторинга запущен. Следящая папка: {WATCH_DIR} ---")

    while True:
        try:
            # Получаем список файлов в папке
            current_files = os.listdir(WATCH_DIR)
            
            # Ищем новые файлы, которых еще не было в списке processed_files
            new_files = [f for f in current_files if f not in processed_files]

            for filename in new_files:
                file_path = os.path.join(WATCH_DIR, filename)
                
                # --- ИСПРАВЛЕНИЕ ---
                # Проверяем, является ли объект файлом. 
                # Если это папка (например, созданная для сортировки), пропускаем её.
                if not os.path.isfile(file_path):
                    continue

                # Простая проверка: если файл слишком маленький (менее 10 байт), 
                # возможно он еще копируется или поврежден.
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < 10:
                        print(f"[WARN] Файл {filename} пустой или поврежден, пропускаем.")
                        processed_files.add(filename)
                        continue
                except Exception as e:
                     # Если не удалось получить размер (например, права доступа), пропускаем
                     print(f"[WARN] Не удалось проверить размер файла {filename}: {e}")
                     processed_files.add(filename)
                     continue

                # Определяем тип файла
                _, ext = os.path.splitext(filename)
                
                if ext in ARCHIVE_EXTENSIONS:
                    process_archive(file_path)
                else:
                    sort_and_move_file(file_path)
                
                # Добавляем файл в список обработанных, чтобы не трогать его снова
                processed_files.add(filename)

        except Exception as e:
            print(f"[ERROR] Общая ошибка цикла мониторинга: {e}")

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
