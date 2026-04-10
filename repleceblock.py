import os

# Определяем путь к папке
folder_path = "./"

# ============================================================
# НАСТРОЙКА: старый и новый код для замены
# ============================================================

old_code = (
    """        <nav id="navbar" class="navbar">
          <ul>
            <li><a href="index.html" class="active">Главная</a></li>

            <li class="dropdown">
              <a href="#"
                ><span>Предприятие</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
                <li><a href="about.html">О нас</a></li>
                <li><a href="history.html">История</a></li>
                <li><a href="goals.html">Цели и задачи</a></li>
                <li><a href="requisites.html">Реквизиты</a></li>
                <li><a href="certificates.html">Аттестаты и сертификаты</a></li>
                <li><a href="team.html">Сотрудники</a></li>
                <li><a href="corruption.html">Противодействие коррупции</a></li>
                <li>
                  <a href="idiology.html">Идеологическая работа</a>
                </li>
                <li><a href="procedure.html">Административные процедуры</a></li>
                <li><a href="feedback.html">Отзывы</a></li>
              </ul>
            </li>
            <li class="dropdown">
              <a href="#"
                ><span>Услуги</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
                <li class="dropdown">
                  <a href="confirmation.html"
                    ><span>Подтверждение<br />соответствия</span>
                    <i class="bi bi-chevron-right"></i
                  ></a>
                  <ul>
                    <li>
                      <a href="confirmation.html#confirmation-1"
                        >Основные<br />положения</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-2"
                        >Область<br />аккредитации</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-3"
                        >Сертификация<br />продукции</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-4"
                        >Сертификация работ<br />в строительстве</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-5"
                        >Декларирование</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-6"
                        >Изготовление<br />копий</a
                      >
                    </li>
                  </ul>
                </li>
                <li><a href="tests.html">Испытания</a></li>
                <li>
                  <a href="assessment.html"
                    >Оценка системы<br />производственного<br />котроля</a
                  >
                </li>
                <li><a href="suitability.html">Оценка пригодности</a></li>
                <li>
                  <a href="extra.html">Дополнительные<br />услуги</a>
                </li>
                <li><a href="forms.html">Бланки</a></li>
              </ul>
            </li>
            <li class="dropdown">
              <a href="#"
                ><span>Заказчику</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
                <li>
                  <a href="rights.html">Права и обязанности заявителей</a>
                </li>
                <li><a href="pricing.html">Оплата работ</a></li>
                <li><a href="complaint.html">Жалобы и апелляции</a></li>
              </ul>
            </li>
            <li><a href="blog.html">Новости</a></li>
            <li><a href="contact.html">Контакты</a></li>
            <li class="dropdown">
              <a href="#" class="getstarted" onclick="toggleMenu(event)">
                <span>Связь с нами</span>
              </a>
              <ul id="options-menu" style="display: none">
                <li>
                  <a href="tel:+375162556868" target="_blank">Позвонить</a>
                </li>
                <li>
                  <a
                    href="/cdn-cgi/l/email-protection#472a262e2b07342235332e3469253e"
                    target="_blank"
                    >Написать письмо</a
                  >
                </li>
                <li>
                  <a href="viber://chat?number=%2B375297782476" target="_blank"
                    >Сообщение в Viber</a
                  >
                </li>
                <li>
                  <a href="https://t.me/sertisbrest" target="_blank"
                    >Сообщение в Telegram</a
                  >
                </li>
                <li>
                  <a href="https://wa.me/375297782476" target="_blank"
                    >Сообщение в WhatsApp</a
                  >
                </li>
              </ul>
            </li>
            <script
              data-cfasync="false"
              src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"
            ></script>
            <script>
              function toggleMenu(event) {
                event.preventDefault();
                const menu = document.getElementById("options-menu");
                menu.style.display =
                  menu.style.display === "none" ? "block" : "none";
              }
              document.addEventListener("click", function (event) {
                const menu = document.getElementById("options-menu");
                const target = event.target;
                if (target.closest(".dropdown") === null) {
                  menu.style.display = "none";
                }
              });
            </script>
          </ul>

          <i class="bi bi-list mobile-nav-toggle"></i>
        </nav>"""
)

new_code = """        <nav id="navbar" class="navbar">
          <ul>
            <li><a href="index.html" class="active">Главная</a></li>

            <li class="dropdown">
              <a href="#"
                ><span>Предприятие</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
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
              </ul>
            </li>
            <li class="dropdown">
              <a href="#"
                ><span>Услуги</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
                <li class="dropdown">
                  <a href="confirmation.html"
                    ><span>Подтверждение<br />соответствия</span>
                    <i class="bi bi-chevron-right"></i
                  ></a>
                  <ul>
                    <li>
                      <a href="confirmation.html#confirmation-1"
                        >Основные<br />положения</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-2"
                        >Область<br />аккредитации</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-3"
                        >Сертификация<br />продукции</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-4"
                        >Сертификация работ<br />в строительстве</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-5"
                        >Декларирование</a
                      >
                    </li>
                    <li>
                      <a href="confirmation.html#confirmation-6"
                        >Изготовление<br />копий</a
                      >
                    </li>
                  </ul>
                </li>
                <li><a href="tests.html">Испытания</a></li>
                <li>
                  <a href="assessment.html"
                    >Оценка системы<br />производственного<br />котроля</a
                  >
                </li>
                <li><a href="suitability.html">Оценка пригодности</a></li>
                <li>
                  <a href="extra.html">Дополнительные<br />услуги</a>
                </li>
                <li><a href="forms.html">Бланки</a></li>
              </ul>
            </li>
            <li class="dropdown">
              <a href="#"
                ><span>Заказчику</span> <i class="bi bi-chevron-down"></i
              ></a>
              <ul>
                <li>
                  <a href="rights.html">Права и обязанности заявителей</a>
                </li>
                <li><a href="pricing.html">Оплата работ</a></li>
                <li><a href="complaint.html">Жалобы и апелляции</a></li>
              </ul>
            </li>
            <li><a href="blog.html">Новости</a></li>
            <li><a href="contact.html">Контакты</a></li>
            <li class="dropdown">
              <a href="#" class="getstarted" onclick="toggleMenu(event)">
                <span>Связь с нами</span>
              </a>
              <ul id="options-menu" style="display: none">
                <li>
                  <a href="tel:+375162556868" target="_blank">Позвонить</a>
                </li>
                <li>
                  <a
                    href="/cdn-cgi/l/email-protection#6e030f07022e1d0b1c1a071d400c17"
                    target="_blank"
                    >Написать письмо</a
                  >
                </li>
                <li>
                  <a href="viber://chat?number=%2B375297782476" target="_blank"
                    >Сообщение в Viber</a
                  >
                </li>
                <li>
                  <a href="https://t.me/sertisbrest" target="_blank"
                    >Сообщение в Telegram</a
                  >
                </li>
                <li>
                  <a href="https://wa.me/375297782476" target="_blank"
                    >Сообщение в WhatsApp</a
                  >
                </li>
              </ul>
            </li>
            <script
              data-cfasync="false"
              src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"
            ></script>
            <script>
              function toggleMenu(event) {
                event.preventDefault();
                const menu = document.getElementById("options-menu");
                menu.style.display =
                  menu.style.display === "none" ? "block" : "none";
              }

              // Close the menu if clicking outside of it
              document.addEventListener("click", function (event) {
                const menu = document.getElementById("options-menu");
                const target = event.target;
                if (target.closest(".dropdown") === null) {
                  menu.style.display = "none";
                }
              });
            </script>
          </ul>

          <i class="bi bi-list mobile-nav-toggle"></i>
        </nav>
        <!-- .navbar -->"""

# Уникальная строка для проверки, была ли замена уже сделана
already_replaced_marker = """<li><a href="structure.html">Структура</a></li>"""

# ============================================================

# Счётчики статистики
files_processed = 0
files_modified = 0
files_already_modified = 0
files_no_match = 0
errors = 0

for filename in os.listdir(folder_path):
    if not filename.endswith(".html"):
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
