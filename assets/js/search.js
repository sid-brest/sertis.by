/* ==========================================================================
   Поиск по сайту: лупа в шапке -> модальное окно с живой выдачей
   - индекс search-index.json подгружается лениво (и заранее — при наведении
     на лупу);
   - каждое слово запроса ищется по подстроке, слова комбинируются (И);
   - ранжирование: заголовок страницы > заголовки секций > текст;
   - индекс двуязычный: тексты хранятся парами «русский сегмент / беларускі
     сегмент» (собирается build-search-index.py), поэтому поиск идёт по обоим
     языкам, а выдача показывается на языке режима — без запросов к
     внешним сервисам перевода;
   - выдача: сниппет с подсветкой <mark>, топ-20, навигация стрелками.
   ========================================================================== */
(function () {
  "use strict";

  // От корня сайта: страницы ошибок могут отдаваться с вложенного URL
  var INDEX_URL = "/search-index.json";
  var MAX_WORDS = 8; // больше слов из запроса / ?find= не учитываем
  var MIN_CHARS = 2; // минимум символов для запроса
  var DEBOUNCE_MS = 60; // пауза перед поиском после ввода
  var MAX_RESULTS = 20; // максимум результатов
  var SNIPPET_MIN = 140; // сниппет добирает соседние сегменты до этой длины
  var SNIPPET_MAX = 260; // и обрезается на этой длине
  var MAX_MARKS = 300; // максимум подсвеченных вхождений на странице
  var FIND_TIMEOUT_MS = 15000; // сколько ждём перевод страницы Google Translate
  var FIND_QUIET_MS = 200; // пауза после последней правки DOM перед повторной попыткой

  var indexPromise = null; // ленивая загрузка индекса
  var pages = null; // подготовленные страницы (нормализованные поля)
  var modal = null,
    input = null,
    resultsEl = null,
    statusEl = null,
    triggerBtn = null;
  var activeIdx = -1; // подсвеченный результат (стрелки)
  var currentHits = [];
  var debounceTimer = null;

  /* ------------------------- тексты интерфейса ------------------------- */

  // Интерфейс окна поиска переведён здесь, а не Google Translate: модалка
  // помечена translate="no", чтобы виджет не портил уже готовые строки.
  var UI = {
    ru: {
      minChars: "Введите запрос — минимум " + MIN_CHARS + " символа.",
      moreChars: function (n) {
        return "Ещё " + n + " символ(а)…";
      },
      loading: "Загрузка индекса…",
      loadFail: "Не удалось загрузить индекс поиска. Попробуйте обновить страницу.",
      notFound: "Ничего не найдено.",
      emptyHtml: function (q) {
        return (
          "По запросу <strong>" +
          escapeHtml(q) +
          "</strong> ничего не найдено.<br />Попробуйте другое слово или часть слова (например, «сертиф»)."
        );
      },
      found: function (n, more) {
        return "Найдено: " + n + (more ? " и более" : "");
      },
      placeholder: "Поиск по сайту…",
      label: "Поиск по сайту",
      clear: "Очистить запрос",
      close: "Закрыть поиск",
    },
    be: {
      minChars: "Увядзіце запыт — мінімум " + MIN_CHARS + " сімвалы.",
      moreChars: function (n) {
        return "Яшчэ " + n + " сімвал(ы)…";
      },
      loading: "Загрузка індэкса…",
      loadFail: "Не ўдалося загрузіць індэкс пошуку. Паспрабуйце абнавіць старонку.",
      notFound: "Нічога не знойдзена.",
      emptyHtml: function (q) {
        return (
          "Па запыце <strong>" +
          escapeHtml(q) +
          "</strong> нічога не знойдзена.<br />Паспрабуйце іншае слова або частку слова (напрыклад, «сертыф»)."
        );
      },
      found: function (n, more) {
        return "Знойдзена: " + n + (more ? " і больш" : "");
      },
      placeholder: "Пошук па сайце…",
      label: "Пошук па сайце",
      clear: "Ачысціць запыт",
      close: "Закрыць пошук",
    },
  };

  // Режим беларускай мовы включается cookie googtrans=/ru/be
  // (кнопка переключателя языка) — сайт переводит Google Translate,
  // а поиск использует собственные белорусские тексты индекса.
  function isBeMode() {
    return /(?:^|;\s*)googtrans=\/ru\/be(?:;|$)/.test(document.cookie);
  }

  function ui() {
    return UI[isBeMode() ? "be" : "ru"];
  }

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

  function queryWords(q) {
    return norm(q).split(/\s+/).filter(Boolean).slice(0, MAX_WORDS);
  }

  /* ------------------------- индекс ------------------------- */

  // Языковой вариант страницы: заголовок, заголовки секций и текст
  // (склеенные сегменты). norm() сохраняет длину строки, поэтому позиции
  // в нормализованном тексте совпадают с исходным; starts[k] — смещение
  // начала сегмента k в склеенном тексте.
  function makeVariant(title, heads, segs) {
    var starts = [];
    var pos = 0;
    for (var i = 0; i < segs.length; i++) {
      starts.push(pos);
      pos += segs[i].length + 1; // сегменты склеиваются через пробел
    }
    var text = segs.join(" ");
    return {
      title: title,
      ltitle: norm(title),
      lheads: heads.map(function (h) {
        return { t: norm(h.t), id: h.id };
      }),
      segs: segs,
      ltext: norm(text),
      starts: starts,
    };
  }

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(INDEX_URL, { cache: "no-cache" })
        .then(function (resp) {
          if (!resp.ok) throw new Error("HTTP " + resp.status);
          return resp.json();
        })
        .then(function (data) {
          pages = (data.pages || []).map(function (p) {
            var segs = p.segs || [];
            var heads = p.headings || [];
            // BE-вариант есть, если сборка положила перевод в пары
            var hasBe = !!p.titleBe && segs.length > 0 && segs[0].length > 1;
            return {
              url: p.url,
              ru: makeVariant(
                p.title,
                heads.map(function (h) {
                  return { t: h.t, id: h.id || "" };
                }),
                segs.map(function (s) {
                  return s[0];
                })
              ),
              be: hasBe
                ? makeVariant(
                    p.titleBe,
                    heads.map(function (h) {
                      return { t: h.b || h.t, id: h.id || "" };
                    }),
                    segs.map(function (s) {
                      return s[1];
                    })
                  )
                : null,
            };
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

  // Оценка слова в варианте страницы: заголовок x5 (x6 с начала слова),
  // заголовок секции x3 (x4 с начала), текст x1.
  function wordScore(v, w) {
    var best = -1;
    var inTitle = false;
    var headingHit = -1;

    var pos = v.ltitle.indexOf(w);
    if (pos >= 0) {
      var startBonus =
        pos === 0 || /[\s\-—–(«"']/.test(v.ltitle.charAt(pos - 1));
      best = startBonus ? 6 : 5;
      inTitle = true;
    }

    for (var i = 0; i < v.lheads.length; i++) {
      var hp = v.lheads[i].t.indexOf(w);
      if (hp >= 0) {
        var hStart =
          hp === 0 || /[\s\-—–(«"']/.test(v.lheads[i].t.charAt(hp - 1));
        var hs = hStart ? 4 : 3;
        if (hs > best) {
          best = hs;
          headingHit = i;
        }
      }
    }

    if (v.ltext.indexOf(w) >= 0 && 1 > best) {
      best = 1;
      headingHit = -1;
    }

    if (best < 0) return null; // слово не найдено на странице
    return { score: best, heading: inTitle ? -1 : headingHit };
  }

  // Оценка всех слов запроса в одном варианте (И); null — нет совпадений
  function scoreVariant(v, words) {
    var total = 0;
    var anchorHeading = -1;
    for (var j = 0; j < words.length; j++) {
      var r = wordScore(v, words[j]);
      if (!r) return null; // И: все слова обязательны
      total += r.score;
      if (anchorHeading < 0 && r.heading >= 0) anchorHeading = r.heading;
    }

    // Небольшой бонус за плотность совпадений в тексте
    var density = 0;
    var from = 0;
    while (density < 5) {
      var p = v.ltext.indexOf(words[0], from);
      if (p < 0) break;
      density++;
      from = p + words[0].length;
    }
    total += density;

    return { score: total, heading: anchorHeading };
  }

  function searchWords(words) {
    // индекс ещё грузится (или не загрузился): искать пока негде
    if (!pages || !words.length) return [];

    var modeBe = isBeMode();
    var hits = [];
    for (var i = 0; i < pages.length; i++) {
      var page = pages[i];
      var ru = scoreVariant(page.ru, words);
      var be = page.be ? scoreVariant(page.be, words) : null;
      if (!ru && !be) continue;

      // В каком варианте совпало: обычно — где оценка выше,
      // при равенстве — язык текущего режима
      var matchBe;
      if (ru && be) {
        matchBe = be.score !== ru.score ? be.score > ru.score : modeBe;
      } else {
        matchBe = !!be;
      }
      var picked = matchBe ? be : ru;
      var variant = matchBe ? page.be : page.ru;

      hits.push({
        page: page,
        score: picked.score,
        anchor: picked.heading >= 0 ? variant.lheads[picked.heading].id : "",
        matchBe: matchBe,
      });
    }

    hits.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.page.url.localeCompare(b.page.url);
    });
    return hits.slice(0, MAX_RESULTS);
  }

  /* ------------------------- выдача ------------------------- */

  // Индекс сегмента, в который попадает позиция pos (бинарный поиск)
  function segmentAt(starts, pos) {
    var lo = 0;
    var hi = starts.length - 1;
    while (lo < hi) {
      var mid = (lo + hi + 1) >> 1;
      if (starts[mid] <= pos) lo = mid;
      else hi = mid - 1;
    }
    return lo;
  }

  // Сниппет: сегмент с первым вхождением любого слова (+ соседние, пока
  // короткий). Совпадение ищется в варианте matchBe, а показывается вариант
  // showBe — это выровненный по сегментам перевод, внешний сервис не нужен.
  // Подсвечиваем слова только если язык показа совпал с языком поиска.
  function buildSnippet(page, words, matchBe, showBe) {
    var m = matchBe ? page.be : page.ru;
    var shown = showBe ? page.be : page.ru;
    var firstPos = -1;
    for (var i = 0; i < words.length; i++) {
      var p = m.ltext.indexOf(words[i]);
      if (p >= 0 && (firstPos < 0 || p < firstPos)) firstPos = p;
    }
    if (firstPos < 0) firstPos = 0;

    var si = segmentAt(m.starts, firstPos);
    var text = shown.segs[si] || "";
    for (var k = si + 1; k < shown.segs.length && text.length < SNIPPET_MIN; k++) {
      text += " " + shown.segs[k];
    }
    var cut = text.length > SNIPPET_MAX;
    if (cut) text = text.slice(0, SNIPPET_MAX);

    var body = matchBe === showBe ? highlight(text, words) : escapeHtml(text);
    return (si > 0 ? "…" : "") + body + (cut ? "…" : "");
  }

  // Оборачивает все вхождения слов в <mark> (экранируя остальной текст)
  function highlight(text, words) {
    var ranges = findRanges(norm(text), words); // та же длина, что и у text
    if (!ranges.length) return escapeHtml(text);

    var out = "";
    var cursor = 0;
    for (var m = 0; m < ranges.length; m++) {
      out += escapeHtml(text.slice(cursor, ranges[m][0]));
      out +=
        "<mark>" + escapeHtml(text.slice(ranges[m][0], ranges[m][1])) + "</mark>";
      cursor = ranges[m][1];
    }
    out += escapeHtml(text.slice(cursor));
    return out;
  }

  // Непересекающиеся диапазоны всех вхождений слов в строке (по порядку)
  function findRanges(lower, words) {
    var ranges = [];
    for (var i = 0; i < words.length; i++) {
      if (!words[i]) continue;
      var from = 0;
      for (;;) {
        var p = lower.indexOf(words[i], from);
        if (p < 0) break;
        ranges.push([p, p + words[i].length]);
        from = p + words[i].length;
      }
    }
    ranges.sort(function (a, b) {
      return a[0] - b[0];
    });
    var merged = [];
    for (var r = 0; r < ranges.length; r++) {
      var last = merged[merged.length - 1];
      if (last && ranges[r][0] <= last[1]) {
        last[1] = Math.max(last[1], ranges[r][1]);
      } else {
        merged.push(ranges[r]);
      }
    }
    return merged;
  }

  function render(query) {
    var words = queryWords(query);
    var t = ui();
    var showBe = isBeMode();

    // индекс ещё грузится: результаты появятся, когда openModal его дождётся
    if (!pages) {
      setStatus(t.loading);
      return;
    }

    if (!words.length) {
      currentHits = [];
      resultsEl.innerHTML = "";
      setStatus(t.minChars);
      return;
    }

    currentHits = searchWords(words);
    activeIdx = -1;
    input.removeAttribute("aria-activedescendant");

    if (!currentHits.length) {
      resultsEl.innerHTML =
        '<li class="search-modal__empty">' + t.emptyHtml(query) + "</li>";
      setStatus(t.notFound);
      return;
    }

    var html = [];
    for (var i = 0; i < currentHits.length; i++) {
      var hit = currentHits[i];
      var page = hit.page;
      // Показываем язык режима, если у страницы есть такой вариант
      var showPageBe = showBe && !!page.be;
      var shown = showPageBe ? page.be : page.ru;
      // ?find — слова запроса, чтобы страница нашла и подсветила место
      // совпадения; &sec — запасной якорь (если find не сработал)
      var href =
        "/" +
        page.url +
        "?find=" +
        encodeURIComponent(words.join(" ")) +
        (hit.anchor ? "&sec=" + encodeURIComponent(hit.anchor) : "");
      var title =
        hit.matchBe === showPageBe
          ? highlight(shown.title, words)
          : escapeHtml(shown.title);
      html.push(
        '<li class="search-result" role="option" id="search-result-' + i + '">' +
          '<a class="search-result__link" href="' +
          escapeHtml(href) +
          '">' +
          '<span class="search-result__title">' +
          title +
          "</span>" +
          '<span class="search-result__url">' +
          escapeHtml(page.url + (hit.anchor ? "#" + hit.anchor : "")) +
          "</span>" +
          '<span class="search-result__snippet">' +
          buildSnippet(page, words, hit.matchBe, showPageBe) +
          "</span>" +
          "</a></li>"
      );
    }
    resultsEl.innerHTML = html.join("");
    setStatus(t.found(currentHits.length, currentHits.length === MAX_RESULTS));
    resultsEl.scrollTop = 0;
  }

  /* ------------------------- модалка ------------------------- */

  function buildModal() {
    if (modal) return modal;

    modal = document.createElement("div");
    modal.className = "search-modal notranslate";
    modal.setAttribute("translate", "no");
    modal.id = "searchModal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML =
      '<div class="search-modal__backdrop" data-search-close></div>' +
      '<div class="search-modal__dialog" role="dialog" aria-modal="true">' +
      '<div class="search-modal__bar">' +
      '<i class="bi bi-search search-modal__icon" aria-hidden="true"></i>' +
      '<input type="text" class="search-modal__input" id="searchInput" ' +
      'autocomplete="off" spellcheck="false" aria-controls="searchResults" />' +
      '<button type="button" class="search-modal__clear" id="searchClear" hidden>' +
      '<i class="bi bi-trash3" aria-hidden="true"></i></button>' +
      '<button type="button" class="search-modal__close" data-search-close>' +
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
        var len = norm(q).length;
        if (len < MIN_CHARS) {
          currentHits = [];
          resultsEl.innerHTML = "";
          setStatus(len ? ui().moreChars(MIN_CHARS - len) : ui().minChars);
          return;
        }
        render(q);
      }, DEBOUNCE_MS)
    );

    input.addEventListener("keydown", onInputKey);
    modal.addEventListener("keydown", trapTab);

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
      setStatus(ui().minChars);
      input.focus();
    });

    return modal;
  }

  // Подписи кнопок и подсказка — на языке режима (обновляются при открытии)
  function applyUiLang() {
    var t = ui();
    input.placeholder = t.placeholder;
    input.setAttribute("aria-label", t.label);
    modal.querySelector(".search-modal__dialog").setAttribute("aria-label", t.label);
    modal.querySelector("#searchClear").setAttribute("aria-label", t.clear);
    modal.querySelector(".search-modal__close").setAttribute("aria-label", t.close);
  }

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function showCurrentQuery() {
    if (norm(input.value).length >= MIN_CHARS) render(input.value);
    else setStatus(ui().minChars);
  }

  function openModal() {
    buildModal();
    applyUiLang();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    input.focus();
    input.select();
    if (!pages) {
      setStatus(ui().loading);
      loadIndex().then(showCurrentQuery, function () {
        setStatus(ui().loadFail);
      });
    } else {
      showCurrentQuery();
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
    // фокус остаётся в поле — скринридеру сообщаем активный результат
    input.setAttribute("aria-activedescendant", el.id);
    el.scrollIntoView({ block: "nearest" });
  }

  // Фокус не уходит из окна поиска на страницу под ним
  function trapTab(e) {
    if (e.key !== "Tab") return;
    var focusable = Array.prototype.filter.call(
      modal.querySelectorAll("input, button"),
      function (el) {
        return !el.hidden && !el.disabled;
      }
    );
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
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

  // Выдача ведёт на страницу с ?find=слова[&sec=якорь]: находим все
  // совпадения в <main>, подсвечиваем и плавно прокручиваем к первому.
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

    var words = queryWords(find);
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
      var marked = markAllMatches(list);
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
    // искомое слово появляется в тексте с задержкой. Вместо опроса по
    // таймеру следим за изменениями DOM: пробуем снова сразу после того,
    // как Google Translate закончил очередную правку.
    var main = document.querySelector("main");
    if (!main || !("MutationObserver" in window)) return;

    var quietTimer = null;
    var giveUpTimer = null;
    var observer = new MutationObserver(function () {
      clearTimeout(quietTimer);
      quietTimer = setTimeout(function () {
        if (tryWords(words)) stop();
      }, FIND_QUIET_MS);
    });
    var stop = function () {
      observer.disconnect();
      clearTimeout(quietTimer);
      clearTimeout(giveUpTimer);
    };

    observer.observe(main, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    giveUpTimer = setTimeout(stop, FIND_TIMEOUT_MS);
  }

  // Оборачивает ВСЕ вхождения слов запроса в <mark class="search-hit">.
  // Условие «И»: если хоть одного слова нет в <main> — не подсвечиваем
  // (вернётся null). Возвращает первую по порядку метку (к ней скроллим).
  function markAllMatches(words) {
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
        if (p.closest("mark.search-hit")) return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue || !node.nodeValue.trim()) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    while (walk.nextNode()) nodes.push(walk.currentNode);

    // Все слова должны встречаться на странице (в склеенном тексте)
    var lowerJoined = norm(
      nodes
        .map(function (n) {
          return n.nodeValue;
        })
        .join(" ")
    );
    for (var i = 0; i < words.length; i++) {
      if (lowerJoined.indexOf(words[i]) < 0) return null;
    }

    var created = [];
    var count = 0;
    for (var n = 0; n < nodes.length && count < MAX_MARKS; n++) {
      var node = nodes[n];
      var text = node.nodeValue;
      var ranges = findRanges(norm(text), words); // norm не меняет длину
      if (!ranges.length) continue;

      var frag = document.createDocumentFragment();
      var cursor = 0;
      for (var r = 0; r < ranges.length && count < MAX_MARKS; r++) {
        if (ranges[r][0] > cursor) {
          frag.appendChild(
            document.createTextNode(text.slice(cursor, ranges[r][0]))
          );
        }
        var wrap = document.createElement("mark");
        wrap.className = "search-hit";
        wrap.textContent = text.slice(ranges[r][0], ranges[r][1]);
        frag.appendChild(wrap);
        created.push(wrap);
        cursor = ranges[r][1];
        count++;
      }
      if (cursor < text.length) {
        frag.appendChild(document.createTextNode(text.slice(cursor)));
      }
      node.parentNode.replaceChild(frag, node);
    }
    if (!created.length) return null;
    // скроллим к первой видимой метке (совпадение может быть в свёрнутом блоке)
    var visible = created.filter(function (m) {
      return m.getClientRects().length > 0;
    });
    return visible.length ? visible[0] : created[0];
  }

  function scrollToMark(el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    // пульсируют все найденные места, а не только первое
    var marks = document.querySelectorAll("mark.search-hit");
    Array.prototype.forEach.call(marks, function (m) {
      m.classList.add("is-pulse");
    });
    // убираем пульсацию, чтобы не висела вечно (подсветка остаётся)
    setTimeout(function () {
      Array.prototype.forEach.call(marks, function (m) {
        m.classList.remove("is-pulse");
      });
    }, 3000);
  }

  /* ------------------------- инициализация ------------------------- */

  function init() {
    triggerBtn = document.getElementById("headerSearchBtn");

    // Ссылки выдачи содержат ?find= — подсвечиваем место на странице
    initFind();

    if (!triggerBtn) return;

    // Индекс качаем заранее, как только пользователь потянулся к поиску —
    // к открытию окна он обычно уже в памяти
    ["pointerenter", "focus", "touchstart"].forEach(function (evt) {
      triggerBtn.addEventListener(
        evt,
        function () {
          loadIndex().catch(function () {});
        },
        { once: true, passive: true }
      );
    });

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
