import os

# Определяем путь к папке
folder_path = "./"

# ============================================================
# НАСТРОЙКА: старый и новый код для замены
# ============================================================

old_code = (
    """<ul>
                <li><a href="team.html">Руководство</a></li>
                <li><a href="structure.html">Структура</a></li>
                <li><a href="about.html">О нас</a></li>
                <li><a href="history.html">История</a></li>
                <li><a href="goals.html">Цели и задачи</a></li>
                <li><a href="requisites.html">Реквизиты</a></li>
                <li><a href="certificates.html">Аттестаты и сертификаты</a></li>
                <li><a href="corruption.html">Противодействие коррупции</a></li>
                <li><a href="idiology.html">Идеологическая работа</a></li>
                <li><a href="procedure.html">Административные процедуры</a></li>
                <li><a href="feedback.html">Отзывы</a></li>
              </ul>"""
)

new_code = """<ul>
                <li><a href="team.html">Руководство</a></li>
                <li><a href="structure.html">Структура</a></li>
                <li><a href="about.html">О нас</a></li>
                <li><a href="history.html">История</a></li>
                <li><a href="goals.html">Цели и задачи</a></li>
                <li><a href="requisites.html">Реквизиты</a></li>
                <li><a href="certificates.html">Аттестаты и сертификаты</a></li>
                <li><a href="corruption.html">Противодействие коррупции</a></li>
                <li><a href="idiology.html">Идеологическая работа</a></li>
                <li><a href="procedure.html">Административные процедуры</a></li>
                <li><a href="profsoyuz.html">Профсоюзная организация</a></li>
                <li><a href="feedback.html">Отзывы</a></li>
              </ul>"""

# Уникальная строка для проверки, была ли замена уже сделана
already_replaced_marker = """<li><a href="profsoyuz.html">Профсоюзная организация</a></li>"""

# ============================================================

# Счётчики статистики
files_processed = 0
files_modified = 0
files_already_modified = 0
files_no_match = 0
errors = 0

for filename in os.listdir(folder_path):
    if not filename.endswith(".shtml"):
        continue

    file_path = os.path.join(folder_path, filename)
    files_processed += 1

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Уже заменено?
        if already_replaced_marker in content:
            print(f"⏭  {filename}: замена уже была сделана ранее. Пропускаем.")
            files_already_modified += 1
            continue

        # Есть что заменять?
        if old_code not in content:
            print(f"⚠️  {filename}: искомый код не найден. Пропускаем.")
            files_no_match += 1
            continue

        # Замена
        new_content = content.replace(old_code, new_code)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ {filename}: замена выполнена успешно.")
        files_modified += 1

    except Exception as e:
        print(f"❌ {filename}: ошибка — {e}")
        errors += 1

# Итоговая статистика
print()
print("=" * 50)
print("Статистика выполнения:")
print("=" * 50)
print(f"Всего HTML-файлов найдено:  {files_processed}")
print(f"Успешно модифицировано:     {files_modified}")
print(f"Уже содержали новый код:    {files_already_modified}")
print(f"Искомый код не найден:      {files_no_match}")
print(f"Ошибок при обработке:       {errors}")
print("=" * 50)
