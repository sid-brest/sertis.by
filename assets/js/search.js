/* ==========================================================================
   Поиск по сайту: лупа в шапке -> модальное окно с живой выдачей
   - индекс search-index.json подгружается лениво при первом открытии;
   - каждое слово запроса ищется по подстроке, слова комбинируются (И);
   - ранжирование: заголовок страницы > заголовки секций > текст;
   - выдача: сниппет с подсветкой <mark>, топ-20, навигация стрелками.
   ========================================================================== */
(function () {
  "use strict";

  var INDEX_URL = "search-index.json";
  var MIN_CHARS = 2; // минимум символов для запроса
  var DEBOUNCE_MS = 150; // пауза перед поиском после ввода
  var MAX_RESULTS = 20; // максимум результатов
  var SNIPPET_BEFORE = 60; // знаков до совпадения в сниппете
  var SNIPPET_AFTER = 130; // знаков после совпадения в сниппете

  var indexPromise = null; // ленивая загрузка индекса
  var pages = null; // подготовленные страницы (нормализованные поля)
  var modal = null,
    input = null,
    resultsEl = null,
    statusEl = null,
    triggerBtn = null;
  var activeIdx = -1; // подсвеченный результат (стрелки)
  var searchToken = 0; // защита от гонки при переводе запроса
  var currentHits = [];
  var debounceTimer = null;

  /* ------------------------- утилиты ------------------------- */

  // Нормализация текста: нижний регистр, ё -> е
  function norm(s) {
    return s.toLowerCase().replace(/ё/g, "е");
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c];
    });
  }

  function debounce(fn, ms) {
    return function () {
      var args = arguments,
        self = this;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        fn.apply(self, args);
      }, ms);
    };
  }

  /* ------------------------- индекс ------------------------- */

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(INDEX_URL, { cache: "no-cache" })
        .then(function (resp) {
          if (!resp.ok) throw new Error("HTTP " + resp.status);
          return resp.json();
        })
        .then(function (data) {
          // Нормализованные копии считаем один раз и кэшируем.
          // toLowerCase() и замена ё->е сохраняют длину строки,
          // поэтому позиции совпадений совпадают с исходным текстом
          // и могут использоваться для построения сниппета.
          pages = (data.pages || []).map(function (p) {
            p.ltitle = norm(p.title);
            p.lheads = (p.headings || []).map(function (h) {
              return { t: norm(h.t), id: h.id || "" };
            });
            p.ltext = norm(p.text);
            return p;
          });
          return pages;
        })
        .catch(function (err) {
          indexPromise = null; // даём шанс повторной загрузке
          throw err;
        });
    }
    return indexPromise;
  }

  /* ------------------------- поиск ------------------------- */

  // Оценка слова на странице: заголовок x5 (x6 с начала слова),
  // заголовок секции x3 (x4 с начала), текст x1
  function wordScore(page, w) {
    var best = -1;
    var inTitle = false;
    var headingHit = -1;

    var pos = page.ltitle.indexOf(w);
    if (pos >= 0) {
      var startBonus =
        pos === 0 || /[\s\-—–(«"']/.test(page.ltitle.charAt(pos - 1));
      best = startBonus ? 6 : 5;
      inTitle = true;
    }

    for (var i = 0; i < page.lheads.length; i++) {
      var hp = page.lheads[i].t.indexOf(w);
      if (hp >= 0) {
        var hStart =
          hp === 0 || /[\s\-—–(«"']/.test(page.lheads[i].t.charAt(hp - 1));
        var hs = hStart ? 4 : 3;
        if (hs > best) {
          best = hs;
          headingHit = i;
        }
      }
    }

    var bp = page.ltext.indexOf(w);
    if (bp >= 0 && 1 > best) {
      best = 1;
      headingHit = -1;
    }

    if (best < 0) return null; // слово не найдено на странице
    return { score: best, heading: inTitle ? -1 : headingHit };
  }

  function searchWords(words) {
    if (!words.length) return [];

    var hits = [];
    for (var i = 0; i < pages.length; i++) {
      var page = pages[i];
      var total = 0;
      var anchorHeading = -1;
      var ok = true;

      for (var j = 0; j < words.length; j++) {
        var r = wordScore(page, words[j]);
        if (!r) {
          ok = false; // И: все слова обязательны
          break;
        }
        total += r.score;
        if (anchorHeading < 0 && r.heading >= 0) anchorHeading = r.heading;
      }
      if (!ok) continue;

      // Небольшой бонус за плотность совпадений в тексте
      var density = 0;
      var from = 0;
      while (density < 5) {
        var p = page.ltext.indexOf(words[0], from);
        if (p < 0) break;
        density++;
        from = p + words[0].length;
      }
      total += density;

      hits.push({ page: page, score: total, heading: anchorHeading });
    }

    hits.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.page.url.localeCompare(b.page.url);
    });
    return hits.slice(0, MAX_RESULTS);
  }

  /* ------------------------- выдача ------------------------- */

  // Сниппет: первое вхождение любого слова запроса в центре фрагмента
  function buildSnippet(page, words) {
    var text = page.ltext;
    var firstPos = -1;
    for (var i = 0; i < words.length; i++) {
      var p = text.indexOf(words[i]);
      if (p >= 0 && (firstPos < 0 || p < firstPos)) firstPos = p;
    }
    if (firstPos < 0) firstPos = 0;

    var start = Math.max(0, firstPos - SNIPPET_BEFORE);
    var end = Math.min(text.length, firstPos + SNIPPET_AFTER);
    var frag = page.text.slice(start, end);

    return (
      (start > 0 ? "…" : "") +
      highlight(frag, words) +
      (end < text.length ? "…" : "")
    );
  }

  // Оборачивает все вхождения слов в <mark> (экранируя остальной текст)
  function highlight(text, words) {
    var ranges = [];
    var lower = norm(text); // та же длина, что и у text
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!w) continue;
      var from = 0;
      for (;;) {
        var p = lower.indexOf(w, from);
        if (p < 0) break;
        ranges.push([p, p + w.length]);
        from = p + w.length;
      }
    }
    if (!ranges.length) return escapeHtml(text);

    ranges.sort(function (a, b) {
      return a[0] - b[0];
    });
    var merged = [ranges[0]];
    for (var r = 1; r < ranges.length; r++) {
      var last = merged[merged.length - 1];
      if (ranges[r][0] <= last[1]) last[1] = Math.max(last[1], ranges[r][1]);
      else merged.push(ranges[r]);
    }

    var out = "";
    var cursor = 0;
    for (var m = 0; m < merged.length; m++) {
      out += escapeHtml(text.slice(cursor, merged[m][0]));
      out += "<mark>" + escapeHtml(text.slice(merged[m][0], merged[m][1])) + "</mark>";
      cursor = merged[m][1];
    }
    out += escapeHtml(text.slice(cursor));
    return out;
  }

  // matchWords — слова, по которым искать в индексе (например, после
  // перевода запроса с беларускай мовы); note — доп. пояснение в статусе
  function render(query, matchWords, note) {
    var words = matchWords || norm(query).split(/\s+/).filter(Boolean);

    if (!words.length) {
      currentHits = [];
      resultsEl.innerHTML = "";
      statusEl.textContent = "Введите запрос — минимум " + MIN_CHARS + " символа.";
      return;
    }

    currentHits = searchWords(words);
    activeIdx = -1;

    if (!currentHits.length) {
      resultsEl.innerHTML =
        '<li class="search-modal__empty">По запросу <strong>' +
        escapeHtml(query) +
        "</strong> ничего не найдено.<br />Попробуйте другое слово или часть слова (например, «сертиф»).</li>";
      statusEl.textContent = "Ничего не найдено.";
      return;
    }

    var html = [];
    for (var i = 0; i < currentHits.length; i++) {
      var hit = currentHits[i];
      var page = hit.page;
      var anchor =
        hit.heading >= 0 && page.headings[hit.heading].id
          ? "#" + page.headings[hit.heading].id
          : "";
      html.push(
        '<li class="search-result" role="option" id="search-result-' + i + '">' +
          '<a class="search-result__link" href="' +
          escapeHtml(page.url + anchor) +
          '">' +
          '<span class="search-result__title">' +
          highlight(page.title, words) +
          "</span>" +
          '<span class="search-result__url">' +
          escapeHtml(page.url + anchor) +
          "</span>" +
          '<span class="search-result__snippet">' +
          buildSnippet(page, words) +
          "</span>" +
          "</a></li>"
      );
    }
    resultsEl.innerHTML = html.join("");
    statusEl.textContent =
      "Найдено: " +
      currentHits.length +
      (currentHits.length === MAX_RESULTS ? " и более" : "") +
      (note ? " — " + note : "");
    resultsEl.scrollTop = 0;
    // В режиме BE результаты показываем на беларускай мове
    // (Google Translate контент модалки не переводит — делаем сами)
    if (isBeMode()) translateResultsToBe();
  }

  /* --------- режим BE: перевод выдачи на беларускую --------- */

  var beCache = Object.create(null); // кэш переводов: русский -> беларуский

  // Пакетный перевод строк через тот же Google Translate (sl=ru, tl=be).
  // Строки соединяются через "\n" и разъединяются обратно.
  function translateBatchToBe(texts) {
    var url =
      "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=be&dt=t&q=" +
      encodeURIComponent(texts.join("\n"));
    return fetch(url).then(function (resp) {
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      return resp.json().then(function (data) {
        var out = (data[0] || [])
          .map(function (seg) {
            return seg[0];
          })
          .join("");
        var lines = out.split("\n");
        // Если Google разбил строки иначе — отказываемся (остаёмся на русском)
        return lines.length === texts.length ? lines : null;
      });
    });
  }

  // Переводит текстовые узлы выдачи (заголовки, сниппеты, статус),
  // сохраняя <mark>-подсветку: узлы и так разделены тегами <mark>,
  // поэтому каждый кусок переводится отдельно и остаётся на своём месте.
  function translateResultsToBe() {
    var targets = [statusEl].concat(
      Array.prototype.slice.call(
        resultsEl.querySelectorAll(
          ".search-result__title, .search-result__snippet, .search-modal__empty"
        )
      )
    );
    var pairs = []; // {node, src}
    var todo = []; // уникальные строки без кэша
    var seen = Object.create(null);

    // собираем ВСЕ текстовые узлы, включая находящиеся внутри <mark> —
    // тогда каждый кусок подсветки переводится отдельно и остаётся на месте
    var collect = function (node) {
      if (node.nodeType === 3) {
        var src = node.nodeValue;
        if (!src.trim()) return;
        pairs.push({ node: node, src: src });
        if (!(src in beCache) && !seen[src]) {
          seen[src] = true;
          todo.push(src);
        }
        return;
      }
      if (node.nodeType === 1) {
        Array.prototype.slice.call(node.childNodes).forEach(collect);
      }
    };
    targets.forEach(function (el) {
      if (el) collect(el);
    });
    if (!pairs.length) return;

    var apply = function () {
      pairs.forEach(function (p) {
        // применяем только если узел жив и текст не менялся с момента сбора
        if (p.node.isConnected && p.node.nodeValue === p.src && beCache[p.src]) {
          p.node.nodeValue = beCache[p.src];
        }
      });
    };

    if (!todo.length) {
      apply();
      return;
    }
    translateBatchToBe(todo).then(
      function (lines) {
        if (!lines) return; // не совпало разбиение — оставляем русский
        todo.forEach(function (src, i) {
          beCache[src] = lines[i];
        });
        apply();
      },
      function () {
        // перевод недоступен — результаты остаются на русском
      }
    );
  }

  /* --------- режим BE: перевод запроса перед поиском --------- */

  // Режим беларускай мовы включается cookie googtrans=/ru/be
  // (кнопка переключателя языка) — страницу переводит Google Translate,
  // а индекс поиска остаётся русским.
  function isBeMode() {
    return /(?:^|;\s*)googtrans=\/ru\/be(?:;|$)/.test(document.cookie);
  }

  // Перевод запроса с беларускай на русский (тот же Google Translate,
  // что переводит сайт; запрос уходит только при пустой выдаче)
  var queryCache = Object.create(null);
  function translateQuery(q) {
    var key = norm(q);
    if (queryCache[key]) return Promise.resolve(queryCache[key]);
    var url =
      "https://translate.googleapis.com/translate_a/single?client=gtx&sl=be&tl=ru&dt=t&q=" +
      encodeURIComponent(q);
    return fetch(url).then(function (resp) {
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      return resp.json().then(function (data) {
        var out = (data[0] || [])
          .map(function (seg) {
            return seg[0];
          })
          .join("")
          .trim();
        if (out) queryCache[key] = out;
        return out;
      });
    });
  }

  // Поиск: сначала как есть; в режиме BE при пустой выдаче —
  // переводим запрос и ищем повторно (устаревшие ответы отбрасываем)
  function runSearch(query) {
    var token = ++searchToken;
    var words = norm(query).split(/\s+/).filter(Boolean);
    var hits = searchWords(words);
    if (hits.length || !isBeMode()) {
      render(query, words);
      return;
    }
    setStatus("Переводим запрос…");
    translateQuery(query).then(
      function (tr) {
        if (token !== searchToken) return;
        var same = !tr || norm(tr) === norm(query);
        var twords = same ? words : norm(tr).split(/\s+/).filter(Boolean);
        var thits = searchWords(twords);
        render(
          query,
          twords,
          !same && thits.length ? "переведено: «" + tr + "»" : ""
        );
      },
      function () {
        if (token !== searchToken) return;
        render(query, words);
      }
    );
  }

  /* ------------------------- модалка ------------------------- */

  function buildModal() {
    if (modal) return modal;

    modal = document.createElement("div");
    modal.className = "search-modal";
    modal.id = "searchModal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML =
      '<div class="search-modal__backdrop" data-search-close></div>' +
      '<div class="search-modal__dialog" role="dialog" aria-modal="true" aria-label="Поиск по сайту">' +
      '<div class="search-modal__bar">' +
      '<i class="bi bi-search search-modal__icon" aria-hidden="true"></i>' +
      '<input type="text" class="search-modal__input" id="searchInput" ' +
      'placeholder="Поиск по сайту…" autocomplete="off" spellcheck="false" ' +
      'aria-label="Поиск по сайту" aria-controls="searchResults" />' +
      '<button type="button" class="search-modal__clear" id="searchClear" ' +
      'aria-label="Очистить запрос" hidden>' +
      '<i class="bi bi-trash3" aria-hidden="true"></i></button>' +
      '<button type="button" class="search-modal__close" data-search-close aria-label="Закрыть поиск">' +
      '<i class="bi bi-x-lg" aria-hidden="true"></i></button>' +
      "</div>" +
      '<div class="search-modal__status" id="searchStatus" role="status" aria-live="polite"></div>' +
      '<ul class="search-modal__results" id="searchResults" role="listbox"></ul>' +
      "</div>";
    document.body.appendChild(modal);

    input = modal.querySelector("#searchInput");
    statusEl = modal.querySelector("#searchStatus");
    resultsEl = modal.querySelector("#searchResults");

    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-search-close]")) closeModal();
    });

    input.addEventListener(
      "input",
      debounce(function () {
        var q = input.value;
        if (norm(q).length < MIN_CHARS) {
          currentHits = [];
          resultsEl.innerHTML = "";
          statusEl.textContent = norm(q).length
            ? "Ещё " + (MIN_CHARS - norm(q).length) + " символ(а)…"
            : "Введите запрос — минимум " + MIN_CHARS + " символа.";
          return;
        }
        setStatus("Ищем…");
        runSearch(q);
      }, DEBOUNCE_MS)
    );

    input.addEventListener("keydown", onInputKey);

    // Кнопка-«веник»: очищает поле запроса (видна, только когда есть текст)
    var clearBtn = modal.querySelector("#searchClear");
    input.addEventListener("input", function () {
      clearBtn.hidden = !input.value;
    });
    clearBtn.addEventListener("click", function () {
      input.value = "";
      clearBtn.hidden = true;
      currentHits = [];
      resultsEl.innerHTML = "";
      setStatus("Введите запрос — минимум " + MIN_CHARS + " символа.");
      input.focus();
    });

    return modal;
  }

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function openModal() {
    buildModal();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    input.focus();
    input.select();
    if (!pages) {
      setStatus("Загрузка индекса…");
      loadIndex().then(
        function () {
          if (input.value.trim().length >= MIN_CHARS) runSearch(input.value);
          else setStatus("Введите запрос — минимум " + MIN_CHARS + " символа.");
        },
        function () {
          setStatus(
            "Не удалось загрузить индекс поиска. Попробуйте обновить страницу."
          );
        }
      );
    } else if (input.value.trim().length >= MIN_CHARS) {
      runSearch(input.value);
    } else {
      setStatus("Введите запрос — минимум " + MIN_CHARS + " символа.");
    }
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (triggerBtn) triggerBtn.focus();
  }

  function isOpen() {
    return !!modal && modal.classList.contains("is-open");
  }

  /* ------------------------- клавиатура ------------------------- */

  function moveActive(delta) {
    var items = resultsEl.querySelectorAll(".search-result");
    if (!items.length) return;
    if (activeIdx >= 0 && items[activeIdx]) {
      items[activeIdx].classList.remove("is-active");
      items[activeIdx].removeAttribute("aria-selected");
    }
    activeIdx = (activeIdx + delta + items.length) % items.length;
    var el = items[activeIdx];
    el.classList.add("is-active");
    el.setAttribute("aria-selected", "true");
    el.scrollIntoView({ block: "nearest" });
  }

  function openActive() {
    var items = resultsEl.querySelectorAll(".search-result__link");
    var target = items[activeIdx >= 0 ? activeIdx : 0];
    if (target) {
      window.location.href = target.getAttribute("href");
    }
  }

  function onInputKey(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      moveActive(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      openActive();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeModal();
    }
  }

  /* ------------------------- инициализация ------------------------- */

  function init() {
    triggerBtn = document.getElementById("headerSearchBtn");
    if (!triggerBtn) return;

    triggerBtn.addEventListener("click", function () {
      if (isOpen()) closeModal();
      else openModal();
    });

    document.addEventListener("keydown", function (e) {
      // Ctrl+K / Cmd+K — открыть поиск из любого места страницы
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (!isOpen()) openModal();
        else input.focus();
        return;
      }
      if (e.key === "Escape" && isOpen()) {
        e.preventDefault();
        closeModal();
      }
      // "/" — тоже открывает поиск, если фокус не в поле ввода
      if (
        e.key === "/" &&
        !isOpen() &&
        !/^(INPUT|TEXTAREA|SELECT)$/.test(
          (e.target.tagName || "").toUpperCase()
        ) &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey
      ) {
        e.preventDefault();
        openModal();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
