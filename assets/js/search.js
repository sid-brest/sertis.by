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
            // BE-вариант (собирается скриптом build-search-index.py);
            // если его нет — страница просто ищется по-русски
            if (p.titleBe && p.textBe) {
              p.ltitleBe = norm(p.titleBe);
              p.lheadsBe = (p.headingsBe || p.headings).map(function (h) {
                return { t: norm(h.t), id: h.id || "" };
              });
              p.ltextBe = norm(p.textBe);
            }
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
  // заголовок секции x3 (x4 с начала), текст x1.
  // be=true — беларуский вариант полей (ltitleBe/lheadsBe/ltextBe)
  function wordScore(page, w, be) {
    var title = be ? page.ltitleBe : page.ltitle;
    var heads = be ? page.lheadsBe : page.lheads;
    var text = be ? page.ltextBe : page.ltext;
    if (!text) return null; // запрошенного варианта у страницы нет

    var best = -1;
    var inTitle = false;
    var headingHit = -1;

    var pos = title.indexOf(w);
    if (pos >= 0) {
      var startBonus =
        pos === 0 || /[\s\-—–(«"']/.test(title.charAt(pos - 1));
      best = startBonus ? 6 : 5;
      inTitle = true;
    }

    for (var i = 0; i < heads.length; i++) {
      var hp = heads[i].t.indexOf(w);
      if (hp >= 0) {
        var hStart =
          hp === 0 || /[\s\-—–(«"']/.test(heads[i].t.charAt(hp - 1));
        var hs = hStart ? 4 : 3;
        if (hs > best) {
          best = hs;
          headingHit = i;
        }
      }
    }

    var bp = text.indexOf(w);
    if (bp >= 0 && 1 > best) {
      best = 1;
      headingHit = -1;
    }

    if (best < 0) return null; // слово не найдено на странице
    return { score: best, heading: inTitle ? -1 : headingHit };
  }

  // Оценка всех слов запроса в одном варианте языка (И); null — нет совпадений
  function scoreVariant(page, words, be) {
    var text = be ? page.ltextBe : page.ltext;
    if (!text) return null;

    var total = 0;
    var anchorHeading = -1;
    for (var j = 0; j < words.length; j++) {
      var r = wordScore(page, words[j], be);
      if (!r) return null; // И: все слова обязательны
      total += r.score;
      if (anchorHeading < 0 && r.heading >= 0) anchorHeading = r.heading;
    }

    // Небольшой бонус за плотность совпадений в тексте
    var density = 0;
    var from = 0;
    while (density < 5) {
      var p = text.indexOf(words[0], from);
      if (p < 0) break;
      density++;
      from = p + words[0].length;
    }
    total += density;

    return { score: total, heading: anchorHeading };
  }

  function searchWords(words) {
    if (!words.length) return [];

    var modeBe = isBeMode();
    var hits = [];
    for (var i = 0; i < pages.length; i++) {
      var page = pages[i];
      var ru = scoreVariant(page, words, false);
      var be = page.ltextBe ? scoreVariant(page, words, true) : null;
      if (!ru && !be) continue;

      // Каким вариантом показать: обычно — более высокая оценка,
      // при равенстве — язык текущего режима
      var useBe;
      if (ru && be) {
        useBe = be.score !== ru.score ? be.score > ru.score : modeBe;
      } else {
        useBe = !!be;
      }
      var picked = useBe ? be : ru;

      hits.push({
        page: page,
        score: picked.score,
        heading: picked.heading,
        be: useBe,
      });
    }

    hits.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.page.url.localeCompare(b.page.url);
    });
    return hits.slice(0, MAX_RESULTS);
  }

  /* ------------------------- выдача ------------------------- */

  // Сниппет: первое вхождение любого слова запроса в центре фрагмента.
  // be — какой вариант текста страницы показывать
  function buildSnippet(page, words, be) {
    var text = be ? page.ltextBe : page.ltext;
    var raw = be ? page.textBe : page.text;
    var firstPos = -1;
    for (var i = 0; i < words.length; i++) {
      var p = text.indexOf(words[i]);
      if (p >= 0 && (firstPos < 0 || p < firstPos)) firstPos = p;
    }
    if (firstPos < 0) firstPos = 0;

    var start = Math.max(0, firstPos - SNIPPET_BEFORE);
    var end = Math.min(text.length, firstPos + SNIPPET_AFTER);
    var frag = raw.slice(start, end);

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
      syncResultsLang();
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
      syncResultsLang(); // -> перевод на язык режима (BE)
      return;
    }

    var html = [];
    for (var i = 0; i < currentHits.length; i++) {
      var hit = currentHits[i];
      var page = hit.page;
      var anchor =
        hit.heading >= 0 && page.headings[hit.heading].id
          ? page.headings[hit.heading].id
          : "";
      var title = hit.be && page.titleBe ? page.titleBe : page.title;
      // ?find — слова запроса, чтобы страница нашла и подсветила место
      // совпадения; &sec — запасной якорь (если find не сработал)
      var href =
        page.url +
        "?find=" +
        encodeURIComponent(words.join(" ")) +
        (anchor ? "&sec=" + encodeURIComponent(anchor) : "");
      html.push(
        '<li class="search-result" role="option" id="search-result-' + i + '"' +
          ' data-lang="' +
          (hit.be ? "be" : "ru") +
          '">' +
          '<a class="search-result__link" href="' +
          escapeHtml(href) +
          '">' +
          '<span class="search-result__title">' +
          highlight(title, words) +
          "</span>" +
          '<span class="search-result__url">' +
          escapeHtml(page.url + (anchor ? "#" + anchor : "")) +
          "</span>" +
          '<span class="search-result__snippet">' +
          buildSnippet(page, words, hit.be) +
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
    // Статус всегда по-русски, результаты — на языке своего варианта;
    // syncResultsLang доводит всё до языка режима (в RU — no-op)
    syncResultsLang();
  }

  /* --------- перевод выдачи, если её язык ≠ языку режима --------- */

  var trCache = Object.create(null); // кэш: "ru>be": {исходный: перевод}

  // Пакетный перевод строк через тот же Google Translate.
  // Строки соединяются через "\n" и разъединяются обратно.
  function translateBatch(texts, from, to) {
    var url =
      "https://translate.googleapis.com/translate_a/single?client=gtx&sl=" +
      from +
      "&tl=" +
      to +
      "&dt=t&q=" +
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
        // Если Google разбил строки иначе — отказываемся
        return lines.length === texts.length ? lines : null;
      });
    });
  }

  // Переводит выдачу на язык режима там, где она на другом:
  // - статус и пустая выдача всегда пишутся по-русски -> в BE-режиме переводим;
  // - результаты с data-lang, отличным от режима, переводятся в язык режима.
  // <mark>-подсветка сохраняется: текст между тегами переводится отдельно.
  function syncResultsLang() {
    var mode = isBeMode() ? "be" : "ru";
    var pairs = []; // {node, src, from}
    var seen = Object.create(null); // ключ "from|src" -> нет перевода
    var todo = { ru: [], be: [] }; // строки без кэша по направлению

    var collect = function (node, from) {
      if (node.nodeType === 3) {
        var src = node.nodeValue;
        if (!src.trim()) return;
        if (from === mode) return; // уже на языке режима
        var key = from + "|" + src;
        pairs.push({ node: node, src: src, from: from });
        if (!(key in seen)) {
          seen[key] = true;
          if (!trCache[key]) todo[from].push(src);
        }
        return;
      }
      if (node.nodeType === 1) {
        Array.prototype.slice.call(node.childNodes).forEach(function (c) {
          collect(c, from);
        });
      }
    };

    // статус и пустая выдача — русский
    if (statusEl) collect(statusEl, "ru");
    var emptyEl = resultsEl && resultsEl.querySelector(".search-modal__empty");
    if (emptyEl) collect(emptyEl, "ru");

    // результаты — на языке своего data-lang
    if (resultsEl) {
      Array.prototype.slice.call(
        resultsEl.querySelectorAll(".search-result")
      ).forEach(function (li) {
        var lang = li.getAttribute("data-lang") === "be" ? "be" : "ru";
        Array.prototype.slice.call(li.querySelectorAll(".search-result__title, .search-result__snippet")).forEach(function (el) {
          collect(el, lang);
        });
      });
    }
    if (!pairs.length) return;

    var apply = function () {
      pairs.forEach(function (p) {
        var key = p.from + "|" + p.src;
        // применяем только если узел жив и текст не менялся с момента сбора
        if (p.node.isConnected && p.node.nodeValue === p.src && trCache[key]) {
          p.node.nodeValue = trCache[key];
        }
      });
    };

    var dirs = [];
    if (todo.ru.length) dirs.push(["ru", "be"]);
    if (todo.be.length) dirs.push(["be", "ru"]);

    if (!dirs.length) {
      apply();
      return;
    }
    var pending = dirs.length;
    dirs.forEach(function (d) {
      var from = d[0],
        to = d[1];
      translateBatch(todo[from], from, to).then(
        function (lines) {
          if (lines) {
            todo[from].forEach(function (src, i) {
              trCache[from + "|" + src] = lines[i];
            });
          }
          if (--pending === 0) apply();
        },
        function () {
          if (--pending === 0) apply(); // перевод недоступен — что есть, то и показываем
        }
      );
    });
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
          setStatus(
            norm(q).length
              ? "Ещё " + (MIN_CHARS - norm(q).length) + " символ(а)…"
              : "Введите запрос — минимум " + MIN_CHARS + " символа."
          );
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
    // В BE-режиме статус («Ищем…», «Загрузка индекса…») тоже переводим
    if (statusEl && isBeMode()) syncResultsLang();
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

  /* ------------------------- диплинк ?find= ------------------------- */

  // Выдача ведёт на страницу с ?find=слова[&sec=якорь]: находим первое
  // совпадение в <main>, подсвечиваем и плавно прокручиваем к нему.
  // Если слово не нашлось сразу — прокручиваем к якорю &sec (запасной
  // вариант), а поиск слова продолжаем в фоне: Google Translate
  // переводит страницу с задержкой и слово может появиться позже.
  function initFind() {
    var params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    var find = (params.get("find") || "").trim();
    var sec = params.get("sec") || "";
    if (!find && !sec) return;

    // Не даём браузеру самому прыгнуть до нашей обработки
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";

    var words = norm(find).split(/\s+/).filter(Boolean);
    var found = false;
    var secScrolled = false;

    var scrollToSec = function () {
      if (!sec || secScrolled) return;
      var el = document.getElementById(sec);
      if (el) {
        secScrolled = true;
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    var tryWords = function (list) {
      if (found) return true;
      var marked = markFirstMatch(list);
      if (marked) {
        found = true;
        scrollToMark(marked);
        return true;
      }
      return false;
    };

    // Сначала — быстрая попытка; если не вышло и есть якорь, едем к нему
    if (words.length && tryWords(words)) return;
    scrollToSec();
    if (!words.length) return;

    // Google Translate переводит страницу ПОСЛЕ загрузки — в BE-режиме
    // искомое слово появляется в тексте с задержкой. Пробуем несколько раз;
    // если нашли позже — перепрыгиваем с якоря на точное место.
    var attempts = 0;
    var MAX_ATTEMPTS = 30; // ~15 сек: GT переводит страницу не сразу
    var tick = function () {
      if (found) return;
      attempts++;
      if (tryWords(words)) return;
      if (attempts >= MAX_ATTEMPTS) {
        // так и не нашли — пробуем перевод слова (слово могло быть
        // на другом языке, чем текст страницы)
        translateQuery(find).then(
          function (tr) {
            var tw = tr ? norm(tr).split(/\s+/).filter(Boolean) : [];
            if (tw.length) tryWords(tw);
          },
          function () {}
        );
        return;
      }
      setTimeout(tick, 500);
    };
    setTimeout(tick, 500);
  }

  // Оборачивает первое вхождение всех слов запроса (И) в <mark class="search-hit">
  function markFirstMatch(words) {
    var main = document.querySelector("main");
    if (!main) return null;

    var nodes = [];
    var walk = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var p = node.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        var tag = p.tagName;
        if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") {
          return NodeFilter.FILTER_REJECT;
        }
        if (!node.nodeValue || !node.nodeValue.trim()) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    while (walk.nextNode()) nodes.push(walk.currentNode);

    // Позиция каждого слова в склеенном тексте main
    var offsets = []; // {start, end, word}
    var pos = 0;
    var pieces = nodes.map(function (n) {
      return n.nodeValue;
    });
    var joined = pieces.join("");
    var lowerJoined = norm(joined);

    for (var i = 0; i < words.length; i++) {
      var p = lowerJoined.indexOf(words[i]);
      if (p < 0) return null; // хоть одного слова нет — не то место
      offsets.push({ start: p, end: p + words[i].length, word: words[i] });
    }

    // Берём позицию первого слова; помечаем каждое слово в его узле
    var nodeStarts = [];
    var acc = 0;
    for (var n = 0; n < nodes.length; n++) {
      nodeStarts.push(acc);
      acc += pieces[n].length;
    }
    var findNode = function (absPos) {
      for (var k = nodes.length - 1; k >= 0; k--) {
        if (nodeStarts[k] <= absPos) return k;
      }
      return -1;
    };

    // Помечаем с конца, чтобы смещения в узлах не поехали;
    // mark — самое левое совпадение (к нему и прокручиваем)
    offsets.sort(function (a, b) {
      return b.start - a.start;
    });
    var mark = null;
    for (var o = 0; o < offsets.length; o++) {
      var off = offsets[o];
      var ki = findNode(off.start);
      var kj = findNode(off.end - 1);
      if (ki < 0 || ki !== kj) continue; // слово пересекает узлы — пропускаем
      var node = nodes[ki];
      var local = off.start - nodeStarts[ki];
      // отрезаем хвост после слова (слово остаётся в node)
      var tailNode = node.splitText(local + off.word.length);
      var wordText = node.nodeValue.slice(local);
      var headText = node.nodeValue.slice(0, local);

      var wrap = document.createElement("mark");
      wrap.className = "search-hit";
      wrap.textContent = wordText;
      node.nodeValue = headText;
      node.parentNode.insertBefore(wrap, node.nextSibling);
      if (!headText) node.parentNode.removeChild(node);
      if (tailNode.nodeValue) {
        wrap.parentNode.insertBefore(tailNode, wrap.nextSibling);
      }
      // сортировка по убыванию: последняя итерация — самое левое слово
      mark = wrap;
    }
    return mark;
  }

  function scrollToMark(el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("is-pulse");
    // убираем подсветку, чтобы не висела вечно
    setTimeout(function () {
      el.classList.remove("is-pulse");
    }, 3000);
  }

  /* ------------------------- инициализация ------------------------- */

  function init() {
    triggerBtn = document.getElementById("headerSearchBtn");

    // Ссылки выдачи содержат ?find= — подсвечиваем место на странице
    initFind();

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
