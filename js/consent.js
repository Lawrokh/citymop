// =============================================================
// CityMop — Cookie Consent + Google Consent Mode v2
// Vanilla JS, ~1.6 KB, zero dependencies
// =============================================================

(function () {
  'use strict';

  const STORAGE_KEY = 'citymop_consent_v1';
  const COOKIE_POLICY_URL = '/polityka-cookies/';

  // ---- Helpers do Consent Mode v2 ----
  // gtag() jest globalny — ustawiony w <head> ZANIM zaladuje sie GA.
  const updateGtagConsent = (granted) => {
    if (typeof window.gtag !== 'function') return;
    window.gtag('consent', 'update', {
      'analytics_storage': granted ? 'granted' : 'denied',
      'ad_storage': 'denied',           // nie uzywamy reklam
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'functionality_storage': 'granted',
      'security_storage': 'granted'
    });
  };

  // ---- Localstorage helpers ----
  const readConsent = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (_) { return null; }
  };

  const writeConsent = (analyticsGranted) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        v: 1,
        analytics: !!analyticsGranted,
        ts: new Date().toISOString()
      }));
    } catch (_) { /* private mode etc. */ }
  };

  // ---- Banner UI (kompaktowy popup) ----
  const buildBanner = () => {
    const wrap = document.createElement('div');
    wrap.className = 'cookie-popup';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-labelledby', 'cookie-popup-desc');
    wrap.innerHTML = `
      <p id="cookie-popup-desc" class="cookie-popup__text">
        Używamy cookies do analityki. <a href="${COOKIE_POLICY_URL}">Więcej</a>
      </p>
      <div class="cookie-popup__actions">
        <button type="button" class="btn-cookie btn-cookie--secondary" data-consent="essential" aria-label="Odrzuć cookies analityczne">
          Odrzuć
        </button>
        <button type="button" class="btn-cookie btn-cookie--primary" data-consent="all" aria-label="Akceptuj wszystkie cookies">
          Akceptuj
        </button>
      </div>
    `;
    return wrap;
  };

  const showBanner = () => {
    if (document.querySelector('.cookie-popup')) return;
    const banner = buildBanner();
    document.body.appendChild(banner);
    requestAnimationFrame(() => banner.classList.add('is-visible'));

    banner.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-consent]');
      if (!btn) return;
      const choice = btn.getAttribute('data-consent');
      const granted = choice === 'all';
      writeConsent(granted);
      updateGtagConsent(granted);
      banner.classList.remove('is-visible');
      setTimeout(() => banner.remove(), 300);
    });
  };

  // ---- Init ----
  const init = () => {
    const stored = readConsent();
    if (stored) {
      // Uzytkownik juz wybral — zsynchronizuj Consent Mode z zapisem.
      updateGtagConsent(!!stored.analytics);
      return;
    }
    // Brak zapisu — pokaz banner.
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  };

  // ---- Public API ----
  // Stopka ma link "Ustawienia cookies" — pozwala otworzyc banner ponownie.
  window.openCookieSettings = function () {
    // Reset zapisu i pokaz baner od nowa.
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
    const existing = document.querySelector('.cookie-popup');
    if (existing) existing.remove();
    showBanner();
  };

  init();
})();
