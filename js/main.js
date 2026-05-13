// =============================================================
// CityMop — UI interactions
// Vanilla JS, no dependencies, defer-loaded
// =============================================================

(function () {
  'use strict';

  // ---- Analytics helper (GA4 — bezpieczne wywolanie) ----
  // Bezpiecznie wywoluje gtag() jezeli istnieje. Nie wywala strony
  // gdy GA jest zablokowane (uBlock/Ghostery) lub jeszcze sie nie zaladowalo.
  const track = (name, params) => {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('event', name, params || {});
      }
    } catch (_) { /* no-op */ }
  };

  // ---- Tel/email click tracking (delegated, dziala tez na blogu) ----
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    if (href.startsWith('tel:')) {
      track('phone_click', {
        phone_number: href.replace('tel:', ''),
        link_text: (a.textContent || '').trim().slice(0, 80),
        page_location: window.location.href
      });
    } else if (href.startsWith('mailto:')) {
      track('email_click', {
        email_address: href.replace('mailto:', '').split('?')[0],
        link_text: (a.textContent || '').trim().slice(0, 80),
        page_location: window.location.href
      });
    }
  }, { passive: true });

  // ---- Nav scroll state ----
  const nav = document.querySelector('.nav');
  if (nav) {
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ---- Mobile menu ----
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.classList.toggle('active', open);
      toggle.setAttribute('aria-expanded', open);
    });
    links.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        links.classList.remove('open');
        toggle.classList.remove('active');
      });
    });
  }

  // ---- FAQ accordion ----
  document.querySelectorAll('.faq-item').forEach(item => {
    const q = item.querySelector('.faq-q');
    if (!q) return;
    if (q.nextElementSibling && q.nextElementSibling.id) {
      q.setAttribute('aria-controls', q.nextElementSibling.id);
    }
    if (!q.hasAttribute('aria-expanded')) q.setAttribute('aria-expanded', 'false');
    q.addEventListener('click', () => {
      const open = q.getAttribute('aria-expanded') === 'true';
      q.setAttribute('aria-expanded', String(!open));
    });
  });

  // ---- Reveal on scroll ----
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }

  // ---- Bubbles in hero card ----
  const bubblesContainer = document.querySelector('.water-bubbles');
  if (bubblesContainer) {
    for (let i = 0; i < 10; i++) {
      const b = document.createElement('span');
      b.className = 'bubble';
      const size = 8 + Math.random() * 40;
      b.style.cssText = `
        width: ${size}px; height: ${size}px;
        left: ${Math.random() * 100}%;
        animation-delay: ${Math.random() * 12}s;
        animation-duration: ${8 + Math.random() * 8}s;
      `;
      bubblesContainer.appendChild(b);
    }
  }

  // ---- Smooth scroll for hash links ----
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href').slice(1);
      if (!id) return;
      const target = document.getElementById(id);
      if (target) {
        e.preventDefault();
        const top = target.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

  // ---- Contact form → Zapier Webhook ----
  const form = document.getElementById('contact-form');
  if (form) {
    const submitBtn = form.querySelector('#contact-submit');
    const statusEl = form.querySelector('#form-status');
    const loadedAt = Date.now();

    const setStatus = (msg, kind) => {
      statusEl.textContent = msg;
      statusEl.dataset.kind = kind || '';
    };

    const showFieldError = (field, show) => {
      const wrap = field.closest('.field');
      if (!wrap) return;
      wrap.classList.toggle('has-error', !!show);
    };

    const validatePhone = (val) => {
      if (!val) return false;
      const digits = val.replace(/\D/g, '');
      return digits.length >= 9 && digits.length <= 15;
    };

    const validateEmail = (val) => {
      if (!val) return true; // optional
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    };

    form.querySelectorAll('input, select, textarea').forEach((el) => {
      el.addEventListener('input', () => showFieldError(el, false));
      el.addEventListener('change', () => showFieldError(el, false));
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('', '');

      const data = new FormData(form);

      if (data.get('_gotcha')) return; // bot trap
      if (Date.now() - loadedAt < 1500) return; // too fast = bot

      let ok = true;
      const name = (data.get('name') || '').toString().trim();
      const phone = (data.get('phone') || '').toString().trim();
      const email = (data.get('email') || '').toString().trim();
      const service = (data.get('service') || '').toString().trim();
      const consent = form.querySelector('input[name="consent"]').checked;

      if (name.length < 2) { showFieldError(form.querySelector('#f-name'), true); ok = false; }
      if (!validatePhone(phone)) { showFieldError(form.querySelector('#f-phone'), true); ok = false; }
      if (!validateEmail(email)) { showFieldError(form.querySelector('#f-email'), true); ok = false; }
      if (!service) { showFieldError(form.querySelector('#f-service'), true); ok = false; }
      if (!consent) { showFieldError(form.querySelector('input[name="consent"]'), true); ok = false; }

      if (!ok) {
        track('form_submit_fail', { reason: 'validation', service: service || '(empty)' });
        setStatus('Uzupełnij wymagane pola (imię, telefon, usługa, zgoda).', 'error');
        const firstErr = form.querySelector('.field.has-error input, .field.has-error select');
        if (firstErr) firstErr.focus();
        return;
      }

      const webhook = form.dataset.webhook;
      if (!webhook || webhook.includes('REPLACE_ME')) {
        setStatus('Formularz nie jest jeszcze podpięty. Zadzwoń: +48 530 610 336.', 'error');
        return;
      }

      const payload = {
        name,
        phone,
        email,
        service,
        address: (data.get('address') || '').toString().trim(),
        message: (data.get('message') || '').toString().trim(),
        consent: 'yes',
        submitted_at: new Date().toISOString(),
        page_url: window.location.href,
        user_agent: navigator.userAgent
      };

      submitBtn.classList.add('is-loading');
      submitBtn.disabled = true;
      setStatus('Wysyłam zapytanie…', 'loading');

      try {
        await fetch(webhook, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        // GA4 rekomendowany event "generate_lead" — pojawia sie w
        // dashbordzie Conversions automatycznie po pierwszym hicie.
        track('generate_lead', {
          currency: 'PLN',
          value: 0,
          service: service,
          has_email: !!email,
          method: 'website_form'
        });
        setStatus('Dziękujemy! Twoje zapytanie zostało wysłane — oddzwonimy w ciągu 1 dnia roboczego.', 'success');
        form.reset();
      } catch (err) {
        track('form_submit_fail', { reason: 'network', service: service });
        setStatus('Coś poszło nie tak. Zadzwoń bezpośrednio: +48 530 610 336.', 'error');
      } finally {
        submitBtn.classList.remove('is-loading');
        submitBtn.disabled = false;
      }
    });
  }

  // ---- Current year in footer ----
  const y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
