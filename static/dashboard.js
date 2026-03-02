(function dashboardPolling() {
  const pollIntervalMs = 3000;
  const filtersForm = document.getElementById('dashboard-filters');
  const totalDevicesValue = document.getElementById('total-devices-value');
  const totalTestsValue = document.getElementById('total-tests-value');
  const failuresLast7DaysValue = document.getElementById('failures-last-7-days-value');
  const latestStatusTableBody = document.getElementById('latest-status-table-body');
  const recentFailuresTableBody = document.getElementById('recent-failures-table-body');
  const latestStatusPrevButton = document.getElementById('latest-status-prev-page');
  const latestStatusNextButton = document.getElementById('latest-status-next-page');
  const latestStatusPageIndicator = document.getElementById('latest-status-page-indicator');
  const recentFailuresPrevButton = document.getElementById('recent-failures-prev-page');
  const recentFailuresNextButton = document.getElementById('recent-failures-next-page');
  const recentFailuresPageIndicator = document.getElementById('recent-failures-page-indicator');
  const liveStatus = document.getElementById('dashboard-live-status');
  const openExportDialogButton = document.getElementById('open-export-dialog');
  const exportDialog = document.getElementById('export-dialog');
  const exportDialogForm = document.getElementById('export-dialog-form');
  const cancelExportButton = document.getElementById('cancel-export');
  const openPrintDialogButton = document.getElementById('open-print-dialog');
  const printDialog = document.getElementById('print-dialog');
  const printDialogForm = document.getElementById('print-dialog-form');
  const cancelPrintButton = document.getElementById('cancel-print');
  const openImportDialogButton = document.getElementById('open-import-dialog');
  const importDialog = document.getElementById('import-dialog');
  const importDialogForm = document.getElementById('import-dialog-form');
  const cancelImportButton = document.getElementById('cancel-import');
  const importOnceStatus = document.getElementById('import-once-status');
  const exportNavLink = document.querySelector('.app-nav__item[href="/export.zip"]');

  if (!filtersForm || !latestStatusTableBody || !recentFailuresTableBody) {
    return;
  }

  const paginationState = {
    latestStatus: {
      currentPage: 1,
      pageSize: 10,
      totalRows: 0
    },
    recentFailures: {
      currentPage: 1,
      pageSize: 10,
      totalRows: 0
    }
  };

  function getTotalPages(state) {
    return Math.max(1, Math.ceil(state.totalRows / state.pageSize));
  }

  function getPageRows(items, state) {
    const start = (state.currentPage - 1) * state.pageSize;
    return items.slice(start, start + state.pageSize);
  }

  function updatePaginationControls(state, prevButton, nextButton, indicator) {
    const totalPages = getTotalPages(state);
    if (state.currentPage > totalPages) {
      state.currentPage = totalPages;
    }
    if (state.currentPage < 1) {
      state.currentPage = 1;
    }
    if (indicator) {
      indicator.textContent = `Page ${state.currentPage} / ${totalPages}`;
    }
    if (prevButton) {
      prevButton.disabled = state.currentPage <= 1;
    }
    if (nextButton) {
      nextButton.disabled = state.currentPage >= totalPages;
    }
  }

  function getQueryString() {
    const params = new URLSearchParams(new FormData(filtersForm));
    for (const [key, value] of params.entries()) {
      if (!value) {
        params.delete(key);
      }
    }
    return params.toString();
  }

  function textOrDash(value) {
    return value || '-';
  }

  function formatDate(value) {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString();
  }

  function createCell(content, className) {
    const cell = document.createElement('td');
    if (className) {
      cell.className = className;
    }
    if (content instanceof Node) {
      cell.appendChild(content);
    } else {
      cell.textContent = String(content);
    }
    return cell;
  }

  function updateDevices(devices, totalRows) {
    const state = paginationState.latestStatus;
    state.totalRows = Number.isFinite(totalRows) ? totalRows : devices.length;
    updatePaginationControls(state, latestStatusPrevButton, latestStatusNextButton, latestStatusPageIndicator);

    latestStatusTableBody.replaceChildren();
    const pageDevices = getPageRows(devices, state);
    const fragment = document.createDocumentFragment();
    for (const device of pageDevices) {
      const row = document.createElement('tr');
      const result = device.last_result || 'UNKNOWN';
      const serialLink = document.createElement('a');
      serialLink.href = `/device/${device.serial}`;
      serialLink.textContent = device.serial;
      row.appendChild(createCell(serialLink, 'col-serial'));
      row.appendChild(createCell(textOrDash(device.barcode), 'truncate'));
      row.appendChild(createCell(textOrDash(device.organization), 'truncate'));
      row.appendChild(createCell(textOrDash(device.device_type), 'truncate'));
      row.appendChild(createCell(formatDate(device.last_tested_at), 'col-date'));
      row.appendChild(createCell(result, `col-result ${result.toLowerCase()}`));

      const actionButton = document.createElement('button');
      actionButton.type = 'button';
      actionButton.className = 'button button-danger js-delete-device';
      actionButton.dataset.serial = device.serial;
      actionButton.textContent = 'Delete';
      row.appendChild(createCell(actionButton));
      fragment.appendChild(row);
    }
    latestStatusTableBody.appendChild(fragment);
  }

  function updateRecentFailures(failures, totalRows) {
    const state = paginationState.recentFailures;
    state.totalRows = Number.isFinite(totalRows) ? totalRows : failures.length;
    updatePaginationControls(state, recentFailuresPrevButton, recentFailuresNextButton, recentFailuresPageIndicator);

    recentFailuresTableBody.replaceChildren();
    const pageFailures = getPageRows(failures, state);
    const fragment = document.createDocumentFragment();
    for (const failure of pageFailures) {
      const row = document.createElement('tr');
      row.appendChild(createCell(failure.serial, 'col-serial'));
      row.appendChild(createCell(textOrDash(failure.barcode), 'truncate'));
      row.appendChild(createCell(textOrDash(failure.device_type), 'truncate'));
      row.appendChild(createCell(textOrDash(failure.fail_reason), 'truncate'));
      row.appendChild(createCell(formatDate(failure.tested_at), 'col-date'));
      row.appendChild(createCell(failure.result, 'col-result fail'));

      const actionButton = document.createElement('button');
      actionButton.type = 'button';
      actionButton.className = 'button button-danger js-delete-test';
      actionButton.dataset.testId = String(failure.id);
      actionButton.textContent = 'Delete';
      row.appendChild(createCell(actionButton));
      fragment.appendChild(row);
    }
    recentFailuresTableBody.appendChild(fragment);
  }

  async function refreshDashboard() {
    const query = getQueryString();
    const endpoint = query ? `/api/dashboard?${query}` : '/api/dashboard';
    try {
      const response = await fetch(endpoint, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      totalDevicesValue.textContent = String(payload.stats.total_devices);
      totalTestsValue.textContent = String(payload.stats.total_tests);
      failuresLast7DaysValue.textContent = String(payload.failures_last_7_days);
      updateDevices(payload.devices || [], payload.totals?.devices);
      updateRecentFailures(payload.recent_failures || [], payload.totals?.recent_failures);
      liveStatus.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    } catch (_error) {
      liveStatus.textContent = 'Live updates paused, retrying...';
    }
  }

  async function deleteTest(testId) {
    const response = await fetch(`/api/tests/${testId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Delete failed');
  }

  async function deleteDevice(serial) {
    const response = await fetch(`/api/devices/${encodeURIComponent(serial)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Delete failed');
  }

  recentFailuresTableBody.addEventListener('click', async (event) => {
    const button = event.target.closest('.js-delete-test');
    if (!button) return;
    const testId = button.dataset.testId;
    if (!testId || !window.confirm('Delete this result?')) return;
    try {
      await deleteTest(testId);
      paginationState.recentFailures.totalRows = Math.max(0, paginationState.recentFailures.totalRows - 1);
      await refreshDashboard();
    } catch (_error) {
      window.alert('Could not delete result.');
    }
  });

  latestStatusTableBody.addEventListener('click', async (event) => {
    const button = event.target.closest('.js-delete-device');
    if (!button) return;
    const serial = button.dataset.serial;
    if (!serial || !window.confirm(`Delete device ${serial} and all its results?`)) return;
    try {
      await deleteDevice(serial);
      paginationState.latestStatus.totalRows = Math.max(0, paginationState.latestStatus.totalRows - 1);
      await refreshDashboard();
    } catch (_error) {
      window.alert('Could not delete device.');
    }
  });

  function changePage(tableName, offset) {
    const state = paginationState[tableName];
    state.currentPage = Math.min(getTotalPages(state), Math.max(1, state.currentPage + offset));
    refreshDashboard();
  }

  if (latestStatusPrevButton) {
    latestStatusPrevButton.addEventListener('click', () => changePage('latestStatus', -1));
  }
  if (latestStatusNextButton) {
    latestStatusNextButton.addEventListener('click', () => changePage('latestStatus', 1));
  }
  if (recentFailuresPrevButton) {
    recentFailuresPrevButton.addEventListener('click', () => changePage('recentFailures', -1));
  }
  if (recentFailuresNextButton) {
    recentFailuresNextButton.addEventListener('click', () => changePage('recentFailures', 1));
  }

  filtersForm.addEventListener('submit', (event) => {
    event.preventDefault();
    paginationState.latestStatus.currentPage = 1;
    paginationState.recentFailures.currentPage = 1;
    refreshDashboard();
  });

  setInterval(refreshDashboard, pollIntervalMs);
  refreshDashboard();

  if (openExportDialogButton && exportDialog && exportDialogForm) {
    openExportDialogButton.addEventListener('click', () => exportDialog.showModal());
    if (exportNavLink) {
      exportNavLink.addEventListener('click', (event) => {
        event.preventDefault();
        exportDialog.showModal();
      });
    }
    if (cancelExportButton) {
      cancelExportButton.addEventListener('click', () => exportDialog.close());
    }
    exportDialogForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const params = new URLSearchParams();
      const formData = new FormData(exportDialogForm);
      for (const [key, value] of formData.entries()) {
        if (value) params.set(key, String(value));
      }
      if (!formData.has('include_csv')) params.set('include_csv', 'false');
      if (!formData.has('include_certificates')) params.set('include_certificates', 'false');
      const organization = params.get('organization');
      if (!organization) {
        alert('Please choose an organization to export.');
        return;
      }
      window.location.href = `/export.zip?${params.toString()}`;
      exportDialog.close();
    });
  }

  if (openPrintDialogButton && printDialog && printDialogForm) {
    openPrintDialogButton.addEventListener('click', () => printDialog.showModal());
    if (cancelPrintButton) {
      cancelPrintButton.addEventListener('click', () => printDialog.close());
    }
    printDialogForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const params = new URLSearchParams();
      const formData = new FormData(printDialogForm);
      for (const [key, value] of formData.entries()) {
        if (value) params.set(key, String(value));
      }
      if (!formData.has('include_csv')) params.set('include_csv', 'false');
      if (!formData.has('include_certificates')) params.set('include_certificates', 'false');
      const organization = params.get('organization');
      if (!organization) {
        alert('Please choose an organization to print.');
        return;
      }
      window.open(`/print-report?${params.toString()}`, '_blank', 'noopener');
      printDialog.close();
    });
  }

  if (openImportDialogButton && importDialog && importDialogForm) {
    openImportDialogButton.addEventListener('click', () => {
      importOnceStatus.textContent = '';
      importDialog.showModal();
    });

    if (cancelImportButton) {
      cancelImportButton.addEventListener('click', () => importDialog.close());
    }

    importDialogForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(importDialogForm);
      const folderPath = String(formData.get('folder_path') || '').trim();
      if (!folderPath) {
        importOnceStatus.textContent = 'Please provide a folder path.';
        return;
      }

      importOnceStatus.textContent = 'Importing...';
      try {
        const response = await fetch(`/api/import-folder-once?folder_path=${encodeURIComponent(folderPath)}`, {
          method: 'POST'
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || 'Import failed');
        }
        importOnceStatus.textContent = `Imported ${payload.processed}/${payload.total} files from ${payload.folder}. Failed: ${payload.failed}.`;
        await refreshDashboard();
      } catch (error) {
        importOnceStatus.textContent = `Import failed: ${error.message}`;
      }
    });
  }
})();
