/* ==========================================================================
   Согласие на cookie и условная загрузка аналитики
   - технические cookie (язык, выбор в этом окне) нужны для работы сайта и
     согласия не требуют;
   - аналитика (Яндекс.Метрика) загружается ТОЛЬКО после нажатия «Принять»;
   - выбор хранится 365 дней (localStorage + cookie) под теми же именами,
     что и в прежней версии баннера, поэтому ранее сделанный выбор не теряется;
   - передумать можно в любой момент: ссылка «Настройки cookie» в подвале.
   ========================================================================== */
(function () {
  "use strict";

  var METRIKA_ID = 68353321;
  var CHOICE_KEY = "cookieConsentChoice"; // "accepted" | "declined"
  var CHOICE_DAYS = 365;

  /* ------------------------- выбор пользователя ------------------------- */

  function readChoice() {
    try {
      var stored = localStorage.getItem(CHOICE_KEY);
      if (stored === "accepted" || stored === "declined") return stored;
    } catch (e) {
      /* localStorage недоступен (приватный режим) — смотрим cookie */
    }
    var m = document.cookie.match(
      /(?:^|;\s*)cookieConsentChoice=(accepted|declined)/
    );
    return m ? m[1] : null;
  }

  function saveChoice(choice) {
    try {
      localStorage.setItem(CHOICE_KEY, choice);
      localStorage.setItem("cookieConsentMade", "true");
    } catch (e) {
      /* без localStorage остаётся cookie */
    }
    var expires = new Date(
      Date.now() + CHOICE_DAYS * 24 * 60 * 60 * 1000
    ).toUTCString();
    var tail = "; expires=" + expires + "; path=/; SameSite=Lax";
    document.cookie = CHOICE_KEY + "=" + choice + tail;
    // как и раньше — ещё и с явным доменом (старые cookie были такими)
    document.cookie =
      CHOICE_KEY + "=" + choice + tail + "; domain=" + location.hostname;
  }

  /* ------------------------- Яндекс.Метрика ------------------------- */

  var metrikaLoaded = false;

  function loadMetrika() {
    if (metrikaLoaded) return;
    metrikaLoaded = true;
    (function (m, e, t, r, i, k, a) {
      m[i] =
        m[i] ||
        function () {
          (m[i].a = m[i].a || []).push(arguments);
        };
      m[i].l = 1 * new Date();
      k = e.createElement(t);
      a = e.getElementsByTagName(t)[0];
      k.async = 1;
      k.src = r;
      a.parentNode.insertBefore(k, a);
    })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

    window.ym(METRIKA_ID, "init", {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
    });
  }

  // Отзыв согласия: удаляем cookie счётчика (_ym*, _ym_uid и т.п.)
  function clearMetrikaCookies() {
    var names = document.cookie.split(";").map(function (c) {
      return c.split("=")[0].trim();
    });
    var host = location.hostname;
    var parts = host.split(".");
    var domains = ["", host];
    if (parts.length > 2) domains.push(parts.slice(-2).join("."));
    names.forEach(function (name) {
      if (name.indexOf("_ym") !== 0 && name !== "yandexuid" && name !== "ymex") {
        return;
      }
      domains.forEach(function (d) {
        document.cookie =
          name +
          "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/" +
          (d ? "; domain=" + d : "");
      });
    });
  }

  /* ------------------------- баннер ------------------------- */

  var banner = null;

  function hideBanner() {
    if (banner && banner.parentNode) banner.parentNode.removeChild(banner);
    banner = null;
  }

  function choose(choice) {
    var previous = readChoice();
    saveChoice(choice);
    hideBanner();
    if (choice === "accepted") {
      loadMetrika();
    } else if (previous === "accepted") {
      // счётчик уже работал на этой странице — чистим следы и перезагружаем
      clearMetrikaCookies();
      location.reload();
    }
  }

  function showBanner() {
    if (banner) return;
    banner = document.createElement("div");
    banner.className = "cookie-banner";
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Использование файлов cookie");
    banner.innerHTML =
      '<p class="cookie-banner__text">Сайт использует файлы cookie. ' +
      "Технические нужны для его работы, аналитические (Яндекс.Метрика) " +
      "включаются только с вашего согласия.</p>" +
      '<div class="cookie-banner__buttons">' +
      '<button type="button" class="cookie-banner__btn cookie-banner__btn--accept" data-cookie-choice="accepted">Принять</button>' +
      '<button type="button" class="cookie-banner__btn cookie-banner__btn--decline" data-cookie-choice="declined">Отказаться</button>' +
      "</div>";
    banner.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-cookie-choice]");
      if (btn) choose(btn.getAttribute("data-cookie-choice"));
    });
    document.body.appendChild(banner);
  }

  // Ссылка «Настройки cookie» в подвале: вернуть баннер и передумать
  function addSettingsLink() {
    var host =
      document.querySelector("#footer .credits") ||
      document.querySelector("#footer .container:last-child") ||
      document.getElementById("footer");
    if (!host || host.querySelector(".cookie-settings-link")) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cookie-settings-link";
    btn.textContent = "Настройки cookie";
    btn.addEventListener("click", showBanner);
    host.appendChild(btn);
  }

  /* ------------------------- запуск ------------------------- */

  function init() {
    addSettingsLink();
    var choice = readChoice();
    if (choice === "accepted") loadMetrika();
    else if (choice === null) showBanner();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
