(function premiumLibraryIntegrations() {
  const root = document.documentElement;
  const themeToggle = document.getElementById('theme-toggle');
  const organizationList = document.getElementById('organization-breakdown-list');
  const chartCanvas = document.getElementById('organization-chart');
  const latestBody = document.getElementById('latest-status-table-body');
  const testHistoryTable = document.querySelector('.device-history-table');
  const validators = [];

  const toast = window.Notyf
    ? new window.Notyf({
        duration: 2400,
        position: { x: 'right', y: 'top' },
        types: [
          { type: 'info', background: '#2563eb', icon: false },
          { type: 'success', background: '#16a34a', icon: false }
        ]
      })
    : null;

  function initLucide() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  function initTippy() {
    if (typeof window.tippy !== 'function') return;
    window.tippy('[title]', {
      animation: 'scale',
      delay: [60, 0],
      theme: 'light-border',
      maxWidth: 260
    });
  }

  function initFloatingThemeHint() {
    if (!window.FloatingUIDOM || !themeToggle) return;
    const tip = document.createElement('div');
    tip.className = 'floating-hint';
    tip.textContent = 'Theme preference is remembered';
    document.body.appendChild(tip);

    const updatePos = () => {
      window.FloatingUIDOM.computePosition(themeToggle, tip, {
        placement: 'bottom-end',
        middleware: [window.FloatingUIDOM.offset(8), window.FloatingUIDOM.flip(), window.FloatingUIDOM.shift()]
      }).then(({ x, y }) => {
        Object.assign(tip.style, { left: `${x}px`, top: `${y}px` });
      });
    };

    let timeoutId = null;
    themeToggle.addEventListener('mouseenter', () => {
      tip.dataset.open = 'true';
      updatePos();
      if (timeoutId) window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        tip.dataset.open = 'false';
      }, 1600);
    });
  }

  function initGsap() {
    if (!window.gsap) return;
    window.gsap.from('.app-bar', { y: -14, opacity: 0, duration: 0.5, ease: 'power2.out' });
  }

  function initLenis() {
    if (!window.Lenis) return;
    const lenis = new window.Lenis({ duration: 0.9, wheelMultiplier: 0.9 });
    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
  }

  function initValidation() {
    if (!window.JustValidate) return;
    [['#export-dialog-form', ['[name="organization"]']], ['#print-dialog-form', ['[name="organization"]']], ['#import-dialog-form', ['[name="folder_path"]']]].forEach(([selector, fields]) => {
      const form = document.querySelector(selector);
      if (!form) return;
      const v = new window.JustValidate(selector, { errorFieldCssClass: 'is-invalid' });
      fields.forEach((field) => v.addField(field, [{ rule: 'required' }]));
      validators.push(v);
    });
  }

  let organizationChart = null;
  function renderOrgChart() {
    if (!chartCanvas || !window.Chart || !organizationList) return;
    const labels = [];
    const values = [];
    organizationList.querySelectorAll('.org-breakdown__item').forEach((item) => {
      const label = item.querySelector('.org-breakdown__label')?.textContent?.trim();
      const value = Number(item.querySelector('.org-breakdown__value')?.textContent || 0);
      if (label) {
        labels.push(label);
        values.push(value);
      }
    });
    if (organizationChart) organizationChart.destroy();
    organizationChart = new window.Chart(chartCanvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: ['#2563eb', '#06b6d4', '#8b5cf6', '#22c55e', '#f59e0b'] }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } }
      }
    });
  }

  function initGridJs() {
    if (!window.gridjs || !testHistoryTable) return;
    const rows = Array.from(testHistoryTable.querySelectorAll('tbody tr')).map((row) =>
      Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent.trim())
    );
    const headers = Array.from(testHistoryTable.querySelectorAll('thead th')).map((cell) => cell.textContent.trim());
    const container = document.createElement('div');
    container.id = 'device-history-grid';
    testHistoryTable.after(container);
    testHistoryTable.hidden = true;
    new window.gridjs.Grid({
      columns: headers,
      data: rows,
      search: true,
      sort: true,
      pagination: { enabled: true, limit: 12 }
    }).render(container);
  }

  function wireThemeToast() {
    if (!themeToggle || !toast) return;
    themeToggle.addEventListener('click', () => {
      const mode = root.getAttribute('data-theme') === 'dark' ? 'Dark' : 'Light';
      toast.open({ type: 'info', message: `${mode} mode enabled` });
    });
  }

  if (organizationList) {
    const observer = new MutationObserver(() => renderOrgChart());
    observer.observe(organizationList, { childList: true, subtree: true });
  }

  if (latestBody && toast) {
    const exportButton = document.getElementById('latest-status-export-visible');
    exportButton?.addEventListener('click', () => toast.success('Export generated for visible latest-status rows'));
  }

  initLucide();
  initTippy();
  initFloatingThemeHint();
  initGsap();
  initLenis();
  initValidation();
  initGridJs();
  wireThemeToast();
  renderOrgChart();
})();
