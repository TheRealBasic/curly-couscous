(function dashboardEnhancements() {
  const latestSearch = document.getElementById('latest-status-search');
  const recentSearch = document.getElementById('recent-failures-search');
  const latestBody = document.getElementById('latest-status-table-body');
  const recentBody = document.getElementById('recent-failures-table-body');
  const latestExportButton = document.getElementById('latest-status-export-visible');
  const recentExportButton = document.getElementById('recent-failures-export-visible');
  const passRateValue = document.getElementById('pass-rate-value');
  const unknownDevicesValue = document.getElementById('unknown-devices-value');
  const organizationBreakdownList = document.getElementById('organization-breakdown-list');

  const clearFiltersButton = document.getElementById('clear-filters');
  const filtersForm = document.getElementById('dashboard-filters');

  if (!latestBody || !recentBody) return;

  function toCsv(rows) {
    return rows
      .map((row) =>
        row
          .map((value) => {
            const text = String(value ?? '');
            if (/[,"\n]/.test(text)) {
              return `"${text.replace(/"/g, '""')}"`;
            }
            return text;
          })
          .join(',')
      )
      .join('\n');
  }

  function downloadCsv(filename, rows) {
    if (!rows.length) return;
    const csv = toCsv(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function rowMatchesQuery(row, query) {
    if (!query) return true;
    const haystack = row.textContent.toLowerCase();
    return haystack.includes(query.toLowerCase());
  }

  function filterTableRows(tbody, query) {
    const rows = tbody.querySelectorAll('tr');
    let visibleCount = 0;
    for (const row of rows) {
      const visible = rowMatchesQuery(row, query);
      row.hidden = !visible;
      if (visible) visibleCount += 1;
    }
    return visibleCount;
  }

  function getVisibleRowsData(tbody) {
    const headers = Array.from(tbody.closest('table').querySelectorAll('thead th')).map((node) => node.textContent.trim());
    const rows = [headers];
    for (const row of tbody.querySelectorAll('tr:not([hidden])')) {
      const cells = Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent.trim());
      rows.push(cells);
    }
    return rows;
  }


  function makeTableSortable(table, defaultColumn = 0) {
    if (!table) return;
    const headers = table.querySelectorAll('thead th');
    let sortState = { index: defaultColumn, direction: 1 };

    function compareValues(a, b) {
      const numA = Number.parseFloat(a);
      const numB = Number.parseFloat(b);
      if (Number.isFinite(numA) && Number.isFinite(numB)) return numA - numB;
      return a.localeCompare(b, undefined, { sensitivity: 'base' });
    }

    function sortRows(index) {
      if (sortState.index === index) {
        sortState.direction *= -1;
      } else {
        sortState.index = index;
        sortState.direction = 1;
      }

      const tbody = table.querySelector('tbody');
      if (!tbody) return;
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((rowA, rowB) => {
        const a = (rowA.children[index]?.textContent || '').trim();
        const b = (rowB.children[index]?.textContent || '').trim();
        return compareValues(a, b) * sortState.direction;
      });
      tbody.replaceChildren(...rows);
    }

    headers.forEach((header, index) => {
      header.classList.add('sortable-header');
      header.addEventListener('click', () => sortRows(index));
      header.title = 'Click to sort';
    });
  }

  function parseStatus(text) {
    return String(text || '').trim().toUpperCase();
  }

  function refreshSummaryCards() {
    const rows = Array.from(latestBody.querySelectorAll('tr'));
    if (!rows.length) {
      if (passRateValue) passRateValue.textContent = '-';
      if (unknownDevicesValue) unknownDevicesValue.textContent = '-';
      if (organizationBreakdownList) organizationBreakdownList.replaceChildren();
      return;
    }

    let passCount = 0;
    let consideredCount = 0;
    let unknownCount = 0;
    const orgCounts = new Map();

    for (const row of rows) {
      const cells = row.querySelectorAll('td');
      const organization = (cells[2]?.textContent || '-').trim() || '-';
      const result = parseStatus(cells[5]?.textContent);
      orgCounts.set(organization, (orgCounts.get(organization) || 0) + 1);

      if (result === 'UNKNOWN') {
        unknownCount += 1;
      }
      if (result === 'PASS' || result === 'FAIL') {
        consideredCount += 1;
        if (result === 'PASS') passCount += 1;
      }
    }

    const passRate = consideredCount > 0 ? Math.round((passCount / consideredCount) * 1000) / 10 : 0;

    if (passRateValue) {
      passRateValue.textContent = `${passRate}%`;
    }
    if (unknownDevicesValue) {
      unknownDevicesValue.textContent = String(unknownCount);
    }

    if (organizationBreakdownList) {
      organizationBreakdownList.replaceChildren();
      const sorted = Array.from(orgCounts.entries()).sort((a, b) => b[1] - a[1]);
      for (const [org, count] of sorted) {
        const item = document.createElement('div');
        item.className = 'org-breakdown__item';

        const name = document.createElement('span');
        name.className = 'org-breakdown__label';
        name.textContent = org;

        const value = document.createElement('span');
        value.className = 'org-breakdown__value';
        value.textContent = String(count);

        const bar = document.createElement('div');
        bar.className = 'org-breakdown__bar';
        const maxCount = sorted[0]?.[1] || 1;
        bar.style.width = `${Math.max(8, (count / maxCount) * 100)}%`;

        item.appendChild(name);
        item.appendChild(value);
        item.appendChild(bar);
        organizationBreakdownList.appendChild(item);
      }
    }
  }

  if (latestSearch) {
    latestSearch.addEventListener('input', () => {
      filterTableRows(latestBody, latestSearch.value.trim());
    });
  }

  if (recentSearch) {
    recentSearch.addEventListener('input', () => {
      filterTableRows(recentBody, recentSearch.value.trim());
    });
  }

  if (latestExportButton) {
    latestExportButton.addEventListener('click', () => {
      const rows = getVisibleRowsData(latestBody);
      downloadCsv('latest-status-visible.csv', rows);
    });
  }

  if (recentExportButton) {
    recentExportButton.addEventListener('click', () => {
      const rows = getVisibleRowsData(recentBody);
      downloadCsv('recent-failures-visible.csv', rows);
    });
  }

  const observer = new MutationObserver(() => {
    refreshSummaryCards();
    if (latestSearch?.value) {
      filterTableRows(latestBody, latestSearch.value.trim());
    }
    if (recentSearch?.value) {
      filterTableRows(recentBody, recentSearch.value.trim());
    }
  });

  observer.observe(latestBody, { childList: true, subtree: true });
  observer.observe(recentBody, { childList: true, subtree: true });


  makeTableSortable(document.querySelector('#latest-status table'));
  makeTableSortable(document.querySelector('#recent-failures table'));

  refreshSummaryCards();

  if (clearFiltersButton && filtersForm) {
    clearFiltersButton.addEventListener('click', () => {
      for (const element of filtersForm.elements) {
        if (!(element instanceof HTMLInputElement || element instanceof HTMLSelectElement)) continue;
        if (element.type === 'date' || element.type === 'text' || element.tagName === 'SELECT') {
          element.value = '';
        }
      }
      filtersForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.metaKey && !event.ctrlKey && document.activeElement === document.body) {
      event.preventDefault();
      latestSearch?.focus();
    }
  });
})();
