import os

# ============================================================
# НАСТРОЙКА: путь к папке с HTML-файлами
# ============================================================
folder_path = "./"

# ============================================================
# 1. CSS-стили переключателя — вставляются перед </style> в <head>
#    Если тега <style> нет, вставляются перед </head>
# ============================================================
LANG_CSS = """
      /* ====== ПЕРЕКЛЮЧАТЕЛЬ ЯЗЫКА ====== */
      .lang-switcher {
        display: inline-flex;
        align-items: center;
        border: 1.5px solid rgba(213, 35, 45, 0.35);
        border-radius: 4px;
        overflow: hidden;
        margin-left: 14px;
        flex-shrink: 0;
        height: 32px;
      }
      .lang-switcher__btn {
        background: transparent;
        border: none;
        cursor: pointer;
        font-family: "Open Sans", sans-serif;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 0 10px;
        height: 100%;
        color: #556270;
        transition: background 0.18s, color 0.18s;
        line-height: 1;
        text-transform: uppercase;
      }
      .lang-switcher__btn:hover {
        background: rgba(213, 35, 45, 0.08);
        color: #d9232d;
      }
      .lang-switcher__btn.active {
        background: #d9232d;
        color: #fff;
      }
      .lang-switcher__divider {
        width: 1px;
        height: 18px;
        background: rgba(213, 35, 45, 0.3);
        flex-shrink: 0;
      }

      /* Прячем всё лишнее от Google Translate */
      .goog-te-banner-frame,
      .goog-te-menu-frame {
        display: none !important;
      }
      body {
        top: 0 !important;
      }
      .skiptranslate {
        visibility: hidden;
        height: 0 !important;
        overflow: hidden;
      }
      #google_translate_element {
        position: absolute;
        left: -9999px;
        top: -9999px;
        visibility: hidden;
      }
"""

# ============================================================
# 2. HTML переключателя — вставляется в конец .container внутри <header>
#    (после закрывающего тега </nav>)
# ============================================================
LANG_HTML = """
        <!-- ====== ПЕРЕКЛЮЧАТЕЛЬ ЯЗЫКА ====== -->
        <div
          class="lang-switcher"
          id="langSwitcher"
          role="group"
          aria-label="Выбор языка"
        >
          <button
            class="lang-switcher__btn active"
            id="btnRu"
            onclick="setLang('ru')"
            aria-pressed="true"
            title="Русский язык"
          >
            RU
          </button>
          <span class="lang-switcher__divider" aria-hidden="true"></span>
          <button
            class="lang-switcher__btn"
            id="btnBe"
            onclick="setLang('be')"
            aria-pressed="false"
            title="Беларуская мова"
          >
            BE
          </button>
        </div>

        <!-- Скрытый контейнер для Google Translate -->
        <div id="google_translate_element"></div>
"""

# ============================================================
# 3. JS переключателя — вставляется перед </body>
# ============================================================
LANG_JS = """
    <!-- ====== СКРИПТ ПЕРЕКЛЮЧАТЕЛЯ ЯЗЫКА ====== -->
    <script>
      function googleTranslateElementInit() {
        new google.translate.TranslateElement(
          { pageLanguage: "ru", includedLanguages: "be", autoDisplay: false },
          "google_translate_element",
        );
      }
      (function () {
        if (document.getElementById("gt-script")) return;
        var s = document.createElement("script");
        s.id = "gt-script";
        s.src =
          "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
        s.async = true;
        document.body.appendChild(s);
      })();

      function setCookie(name, value) {
        document.cookie = name + "=" + value + "; path=/;";
        document.cookie =
          name + "=" + value + "; path=/; domain=" + location.hostname + ";";
      }

      function setLang(lang) {
        if (lang === "ru") {
          setCookie("googtrans", "");
          document.cookie =
            "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
          document.cookie =
            "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=" +
            location.hostname + ";";
          localStorage.setItem("sertis_lang", "ru");
          location.reload();
          return;
        }
        if (lang === "be") {
          setCookie("googtrans", "/ru/be");
          localStorage.setItem("sertis_lang", "be");
          location.reload();
        }
      }

      document.addEventListener("DOMContentLoaded", function () {
        var btnRu = document.getElementById("btnRu");
        var btnBe = document.getElementById("btnBe");
        var isBe = document.cookie.indexOf("googtrans=/ru/be") !== -1;
        if (isBe) {
          btnRu.classList.remove("active");
          btnRu.setAttribute("aria-pressed", "false");
          btnBe.classList.add("active");
          btnBe.setAttribute("aria-pressed", "true");
        } else {
          btnRu.classList.add("active");
          btnRu.setAttribute("aria-pressed", "true");
          btnBe.classList.remove("active");
          btnBe.setAttribute("aria-pressed", "false");
        }
      });
    </script>
"""

# Маркер для проверки — переключатель уже добавлен
ALREADY_ADDED_MARKER = 'id="langSwitcher"'

# ============================================================
# Вспомогательные функции вставки
# ============================================================


def inject_css(content: str) -> tuple[str, bool]:
    """Вставляет CSS перед закрывающим </style> в <head>.
    Если тега <style> нет — создаёт блок <style> перед </head>."""
    # Ищем </style> в пределах <head>
    head_end = content.lower().find("</head>")
    style_close = content.lower().rfind(
        "</style>", 0, head_end if head_end != -1 else len(content)
    )

    if style_close != -1:
        insert_pos = style_close  # вставляем прямо перед </style>
        new_content = content[:insert_pos] + LANG_CSS + content[insert_pos:]
        return new_content, True

    # Нет <style> — добавляем блок перед </head>
    if head_end != -1:
        style_block = f"\n    <style>{LANG_CSS}    </style>\n"
        new_content = content[:head_end] + style_block + content[head_end:]
        return new_content, True

    return content, False


def inject_html(content: str) -> tuple[str, bool]:
    """Вставляет HTML переключателя после закрывающего </nav> внутри <header>."""
    # Ищем </header> чтобы ограничить область поиска
    header_end = content.lower().find("</header>")
    search_area = content if header_end == -1 else content[:header_end]

    # Последний </nav> в области header
    nav_close = search_area.lower().rfind("</nav>")
    if nav_close == -1:
        return content, False

    # Реальная позиция в исходной строке (учитываем регистр)
    after_nav = nav_close + len("</nav>")
    new_content = content[:after_nav] + "\n" + LANG_HTML + content[after_nav:]
    return new_content, True


def inject_js(content: str) -> tuple[str, bool]:
    """Вставляет JS перед закрывающим </body>."""
    body_close = content.lower().rfind("</body>")
    if body_close == -1:
        return content, False

    new_content = content[:body_close] + LANG_JS + "\n" + content[body_close:]
    return new_content, True


# ============================================================
# Основной цикл
# ============================================================

files_processed = 0
files_modified = 0
files_already_modified = 0
files_no_nav = 0
errors = 0

for filename in sorted(os.listdir(folder_path)):
    if not filename.endswith(".shtml"):
        continue

    file_path = os.path.join(folder_path, filename)
    files_processed += 1

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Уже содержит переключатель?
        if ALREADY_ADDED_MARKER in content:
            print(f"⏭  {filename}: переключатель уже добавлен. Пропускаем.")
            files_already_modified += 1
            continue

        modified = content

        # 1. CSS
        modified, css_ok = inject_css(modified)

        # 2. HTML кнопок
        modified, html_ok = inject_html(modified)

        # 3. JS
        modified, js_ok = inject_js(modified)

        if not html_ok:
            print(f"⚠️  {filename}: тег </nav> внутри <header> не найден. Пропускаем.")
            files_no_nav += 1
            continue

        if not css_ok:
            print(
                f"⚠️  {filename}: не удалось вставить CSS (нет </style> и </head>). Файл сохранён без стилей."
            )

        if not js_ok:
            print(
                f"⚠️  {filename}: не удалось вставить JS (нет </body>). Файл сохранён без скрипта."
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified)

        print(f"✅ {filename}: переключатель языка добавлен.")
        files_modified += 1

    except Exception as e:
        print(f"❌ {filename}: ошибка — {e}")
        errors += 1

# ============================================================
# Итоговая статистика
# ============================================================
print()
print("=" * 50)
print("Статистика выполнения:")
print("=" * 50)
print(f"Всего HTML-файлов найдено:     {files_processed}")
print(f"Успешно модифицировано:        {files_modified}")
print(f"Уже содержали переключатель:   {files_already_modified}")
print(f"Не найден </nav> в <header>:   {files_no_nav}")
print(f"Ошибок при обработке:          {errors}")
print("=" * 50)
