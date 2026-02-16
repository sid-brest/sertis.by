import os

# Определяем путь к папке и маркер для замены
folder_path = "./"

# Старый код, который нужно найти
old_code = """        <!-- <h1 class="logo me-auto"><a href="index.html">Сертис</a></h1> -->
        <!-- Uncomment below if you prefer to use an image logo -->
        <a href="index.html" class="logo me-auto"
          ><img src="assets/img/logo.png" alt="" class="img-fluid"
        /></a>"""

# Новый код, на который нужно заменить
new_code = """        <!-- <h1 class="logo me-auto"><a href="index.html">Сертис</a></h1> -->
        <!-- Uncomment below if you prefer to use an image logo -->
        <div class="logos-container me-auto">
          <a href="index.html" class="logo"
            ><img src="assets/img/logo.png" alt="" class="img-fluid"
          /></a>
          <img src="assets/img/Logo-2026.webp" alt="2026" class="logo-2026 img-fluid" />
        </div>"""

# CSS стили для второго логотипа (нужно вставить в <head> перед </head>)
css_code = """    
    <!-- Custom styles for second logo -->
    <style>
      .logo-2026 {
        margin-left: 15px;
        height: auto;
        max-height: 60px;
        border-radius: 8px;
        object-fit: contain;
      }
      
      .logos-container {
        display: flex;
        align-items: center;
      }
      
      @media (max-width: 768px) {
        .logo-2026 {
          max-height: 45px;
          margin-left: 10px;
        }
      }
    </style>
  </head>"""

# Уникальный идентификатор для проверки, был ли код уже вставлен
logo_identifier = "logo-2026"
css_identifier = "Custom styles for second logo"

# Счетчики для статистики
files_processed = 0
files_modified = 0
files_already_modified = 0
errors = 0

# Итерация по всем файлам в папке
for filename in os.listdir(folder_path):
    if filename.endswith(".html"):
        file_path = os.path.join(folder_path, filename)
        files_processed += 1
        
        try:
            # Чтение содержимого файла
            with open(file_path, "r", encoding="utf-8") as file:
                file_content = file.read()
            
            # Проверка, содержит ли файл уже вставленный код
            if logo_identifier in file_content:
                print(f"Файл {filename} уже содержит второй логотип. Пропускаем.")
                files_already_modified += 1
                continue
            
            modified = False
            
            # Замена старого кода логотипа на новый
            if old_code in file_content:
                file_content = file_content.replace(old_code, new_code)
                print(f"  ✓ Логотип заменен в {filename}")
                modified = True
            else:
                print(f"  ⚠ В файле {filename} не найден старый код логотипа.")
            
            # Добавление CSS стилей перед </head>
            if "</head>" in file_content and css_identifier not in file_content:
                file_content = file_content.replace("  </head>", css_code)
                print(f"  ✓ CSS стили добавлены в {filename}")
                modified = True
            elif css_identifier in file_content:
                print(f"  ℹ CSS стили уже присутствуют в {filename}")
            
            # Если файл был модифицирован, сохраняем изменения
            if modified:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(file_content)
                
                print(f"✅ Код успешно вставлен в файл {filename}\n")
                files_modified += 1
        
        except Exception as e:
            print(f"❌ Ошибка при обработке файла {filename}: {str(e)}\n")
            errors += 1

# Вывод итоговой статистики
print("=" * 50)
print("Статистика выполнения:")
print("=" * 50)
print(f"Всего обработано файлов: {files_processed}")
print(f"Модифицировано файлов: {files_modified}")
print(f"Файлов, уже содержащих второй логотип: {files_already_modified}")
print(f"Ошибок при обработке: {errors}")
print("=" * 50)
