import os

# Определяем путь к папке и индикаторы для вставки
folder_path = "./"
start_marker = "</footer>"
end_marker = "</body>"

# Код, который нужно вставить
code_to_insert = """    <!-- Cookie Consent Banner -->
    <script>
      (function () {
        // Немедленная функция для изоляции переменных

        // Определяем, был ли сделан выбор пользователя ранее
        function hasUserMadeChoice() {
          // Проверяем localStorage
          try {
            if (localStorage.getItem("cookieConsentMade") === "true") {
              return true;
            }
          } catch (e) {
            console.warn("Ошибка доступа к localStorage:", e);
          }

          // Проверяем cookie
          return document.cookie.split(";").some((item) => {
            return item.trim().startsWith("cookieConsentMade=true");
          });
        }

        // Функция для сохранения выбора пользователя
        function saveUserChoice(choice) {
          // Сохраняем в localStorage
          try {
            localStorage.setItem("cookieConsentMade", "true");
            localStorage.setItem("cookieConsentChoice", choice);
          } catch (e) {
            console.warn("LocalStorage не доступен:", e);
          }

          // Сохраняем как cookie с явной областью видимости для всего домена
          const date = new Date();
          date.setTime(date.getTime() + 365 * 24 * 60 * 60 * 1000); // 1 год
          const expires = "expires=" + date.toUTCString();
          const domain = window.location.hostname;

          document.cookie = `cookieConsentMade=true; ${expires}; path=/; domain=${domain}; SameSite=Lax`;
          document.cookie = `cookieConsentChoice=${choice}; ${expires}; path=/; domain=${domain}; SameSite=Lax`;
        }

        // Если пользователь уже сделал выбор, ничего не показываем
        if (hasUserMadeChoice()) {
          console.log("Пользователь уже сделал выбор о cookie");
          return;
        }

        // Создаем и показываем элемент согласия cookie
        function createConsentElement() {
          if (document.getElementById("cookieConsentContainer")) {
            return; // Баннер уже отображается
          }

          // Определение медиа-запроса для мобильных устройств
          const isMobile = window.matchMedia("(max-width: 768px)").matches;

          const element = document.createElement("div");
          element.id = "cookieConsentContainer";
          element.style.cssText = `
      position: fixed; 
      bottom: 0; 
      left: 0; 
      right: 0; 
      background: #2f3640;
      color: #fff; 
      padding: 15px 20px; 
      box-shadow: 0 -2px 15px rgba(0,0,0,0.1); 
      z-index: 9999; 
      font-family: Arial, sans-serif;
    `;

          // Стили кнопок в зависимости от устройства
          const buttonsStyle = isMobile
            ? `display: flex; flex-direction: column; gap: 10px; width: 100%;`
            : `display: flex; gap: 12px;`;

          // Стили для контейнера с общим содержимым
          const containerStyle = isMobile
            ? `max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 15px;`
            : `max-width: 1200px; margin: 0 auto; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 15px;`;

          element.innerHTML = `
      <div style="${containerStyle}">
        <p style="margin: 0; font-size: 14px; line-height: 1.4;">Этот сайт использует файлы cookie для корректной работы.</p>
        <div style="${buttonsStyle}">
          <button id="acceptCookiesBtn" style="min-width: 120px; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; height: 40px; box-sizing: border-box; background: #d9232d; color: white;">Принять</button>
          <button id="declineCookiesBtn" style="min-width: 120px; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; height: 40px; box-sizing: border-box; background: #6c757d; color: white;">Отказаться</button>
        </div>
      </div>
    `;

          document.body.appendChild(element);

          // Добавляем обработчики событий
          document
            .getElementById("acceptCookiesBtn")
            .addEventListener("click", function () {
              saveUserChoice("accepted");
              element.style.display = "none";
            });

          document
            .getElementById("declineCookiesBtn")
            .addEventListener("click", function () {
              saveUserChoice("declined");
              element.style.display = "none";
            });
        }

        // Ждем, пока DOM будет полностью загружен
        if (document.readyState === "loading") {
          document.addEventListener("DOMContentLoaded", createConsentElement);
        } else {
          createConsentElement();
        }

        // Добавляем обработчик изменения размера окна для адаптивности
        window.addEventListener("resize", function () {
          // Удаляем старый баннер, если он есть
          const oldBanner = document.getElementById("cookieConsentContainer");
          if (oldBanner && hasUserMadeChoice() === false) {
            oldBanner.remove();
            createConsentElement();
          }
        });
      })();
    </script>"""

# Уникальный идентификатор для проверки, был ли код уже вставлен
# Используем первые 50 символов кода как идентификатор
code_identifier = code_to_insert[:50]

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
            if code_identifier in file_content:
                print(f"Файл {filename} уже содержит вставленный код. Пропускаем.")
                files_already_modified += 1
                continue
                
            # Проверка наличия начального и конечного маркера
            if start_marker in file_content and end_marker in file_content:
                # Вставка кода между маркерами
                modified_content = file_content.replace(
                    start_marker, 
                    start_marker + "\n" + code_to_insert
                )
                
                # Запись модифицированного содержимого обратно в файл
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(modified_content)
                
                print(f"Код успешно вставлен в файл {filename}")
                files_modified += 1
            else:
                print(f"В файле {filename} не найдены требуемые маркеры. Пропускаем.")
        
        except Exception as e:
            print(f"Ошибка при обработке файла {filename}: {str(e)}")
            errors += 1

# Вывод итоговой статистики
print("\nСтатистика выполнения:")
print(f"Всего обработано файлов: {files_processed}")
print(f"Модифицировано файлов: {files_modified}")
print(f"Файлов, уже содержащих код: {files_already_modified}")
print(f"Ошибок при обработке: {errors}")