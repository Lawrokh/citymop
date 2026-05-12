// =============================================================
// CityMop — UI interactions
// Vanilla JS, no dependencies, defer-loaded
// =============================================================

(function () {
  'use strict';

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
    q.setAttribute('aria-controls', q.nextElementSibling.id || '');
    q.addEventListener('click', () => {
      const open = item.getAttribute('aria-expanded') === 'true';
      // close others optionally; here keep multiple open
      item.setAttribute('aria-expanded', !open);
      q.setAttribute('aria-expanded', !open);
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

  // ---- Contact form (front-end mailto fallback; replace with API) ----
  const form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const subject = encodeURIComponent('Zapytanie ze strony CityMop — ' + (data.get('service') || ''));
      const body = encodeURIComponent(
        `Imię: ${data.get('name')}
` +
        `Telefon: ${data.get('phone')}
` +
        `E-mail: ${data.get('email')}
` +
        `Usługa: ${data.get('service')}
` +
        `Adres: ${data.get('address') || '—'}
` +
        `Wiadomość:
${data.get('message') || '—'}`
      );
      window.location.href = `mailto:info@citymop.pl?subject=${subject}&body=${body}`;
    });
  }

  // ---- Current year in footer ----
  const y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
