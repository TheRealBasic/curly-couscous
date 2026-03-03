(function appUI() {
  const storageKey = 'gasdock.theme';
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');

  function getPreferredTheme() {
    const stored = window.localStorage.getItem(storageKey);
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (toggle) {
      toggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      toggle.setAttribute('title', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }
  }

  applyTheme(getPreferredTheme());

  if (toggle) {
    toggle.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try {
        window.localStorage.setItem(storageKey, next);
      } catch (_error) {
        // Ignore storage restrictions.
      }
    });
  }

  function animateIn() {
    const motionLib = window.Motion;
    if (!motionLib || typeof motionLib.animate !== 'function') return;

    const cards = document.querySelectorAll('.card, .panel, .app-nav__item');
    motionLib.stagger(0.04);
    motionLib.animate(cards, { opacity: [0, 1], y: [10, 0] }, { duration: 0.45, delay: motionLib.stagger(0.04), easing: 'ease-out' });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', animateIn);
  } else {
    animateIn();
  }
})();
