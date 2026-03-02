(function dashboardPolling() {
  const defaultPollIntervalMs = 30000;
  const pollIntervalOptions = new Set([10000, 30000, 60000]);
  const liveUpdatesStorageKey = 'dashboard.liveUpdates.preferences';
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
  const liveUpdatesEnabledInput = document.getElementById('live-updates-enabled');
  const liveUpdatesIntervalSelect = document.getElementById('live-updates-interval');
  const filtersFeedback = document.getElementById('filters-feedback');
  const openExportDialogButton = document.getElementById('open-export-dialog');
  const exportDialog = document.getElementById('export-dialog');
  const exportDialogForm = document.getElementById('export-dialog-form');
  const exportFeedback = document.getElementById('export-feedback');
  const cancelExportButton = document.getElementById('cancel-export');
  const openPrintDialogButton = document.getElementById('open-print-dialog');
  const printDialog = document.getElementById('print-dialog');
  const printDialogForm = document.getElementById('print-dialog-form');
  const printFeedback = document.getElementById('print-feedback');
  const cancelPrintButton = document.getElementById('cancel-print');
  const openImportDialogButton = document.getElementById('open-import-dialog');
  const importDialog = document.getElementById('import-dialog');
  const importDialogForm = document.getElementById('import-dialog-form');
  const cancelImportButton = document.getElementById('cancel-import');
  const importOnceFeedback = document.getElementById('import-once-feedback');
  const exportNavLink = document.querySelector('.app-nav__item[href="/export.zip"]');

  if (!filtersForm || !latestStatusTableBody || !recentFailuresTableBody) {
    return;
  }

  const feedbackTimeouts = new Map();

  const defaultLivePreferences = {
    enabled: true,
    intervalMs: defaultPollIntervalMs
  };

  function parseIntervalMs(value) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed) || !pollIntervalOptions.has(parsed)) {
      return defaultPollIntervalMs;
    }
    return parsed;
  }

  function readLivePreferences() {
    try {
      const raw = window.localStorage.getItem(liveUpdatesStorageKey);
      if (!raw) return { ...defaultLivePreferences };
      const parsed = JSON.parse(raw);
      return {
        enabled: typeof parsed.enabled === 'boolean' ? parsed.enabled : defaultLivePreferences.enabled,
        intervalMs: parseIntervalMs(parsed.intervalMs)
      };
    } catch (_error) {
      return { ...defaultLivePreferences };
    }
  }

  function saveLivePreferences(preferences) {
    try {
      window.localStorage.setItem(liveUpdatesStorageKey, JSON.stringify(preferences));
    } catch (_error) {
      // Ignore storage failures in restricted browser modes.
    }
  }

  let refreshTimerId = null;
  const livePreferences = readLivePreferences();

  function updateLiveStatus(lastUpdatedAt = null) {
    if (!liveStatus) return;
    const intervalSeconds = Math.floor(livePreferences.intervalMs / 1000);
    const modeText = livePreferences.enabled ? `Updating every ${intervalSeconds}s` : 'Paused';
    if (!lastUpdatedAt) {
      liveStatus.textContent = modeText;
      return;
    }
    liveStatus.textContent = `${modeText} · Last updated: ${lastUpdatedAt.toLocaleTimeString()}`;
  }

  function stopRefreshTimer() {
    if (refreshTimerId !== null) {
      window.clearInterval(refreshTimerId);
      refreshTimerId = null;
    }
  }

  function startRefreshTimer() {
    stopRefreshTimer();
    if (!livePreferences.enabled) return;
    refreshTimerId = window.setInterval(() => {
      refreshDashboard();
    }, livePreferences.intervalMs);
  }

  function syncLiveControls() {
    if (liveUpdatesEnabledInput) {
      liveUpdatesEnabledInput.checked = livePreferences.enabled;
    }
    if (liveUpdatesIntervalSelect) {
      liveUpdatesIntervalSelect.value = String(livePreferences.intervalMs);
      liveUpdatesIntervalSelect.disabled = !livePreferences.enabled;
    }
  }


  function clearFeedback(feedbackEl) {
    if (!feedbackEl) return;
    const timeoutId = feedbackTimeouts.get(feedbackEl);
    if (timeoutId) {
      window.clearTimeout(timeoutId);
      feedbackTimeouts.delete(feedbackEl);
    }
    const messageNode = feedbackEl.querySelector('.feedback-message');
    if (messageNode) messageNode.textContent = '';
    feedbackEl.hidden = true;
  }

  function showFeedback(feedbackEl, message, type = 'error', autoClearMs = 0) {
    if (!feedbackEl) return;
    const messageNode = feedbackEl.querySelector('.feedback-message');
    if (messageNode) messageNode.textContent = message;
    feedbackEl.dataset.state = type;
    feedbackEl.hidden = false;

    const existing = feedbackTimeouts.get(feedbackEl);
    if (existing) window.clearTimeout(existing);
    if (autoClearMs > 0) {
      const timeoutId = window.setTimeout(() => {
        clearFeedback(feedbackEl);
      }, autoClearMs);
      feedbackTimeouts.set(feedbackEl, timeoutId);
    }
  }

  function attachDismissHandlers() {
    for (const button of document.querySelectorAll('[data-feedback-dismiss]')) {
      button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-feedback-dismiss');
        clearFeedback(document.getElementById(targetId));
      });
    }
  }

  function clearFieldError(field) {
    if (!field) return;
    field.removeAttribute('aria-invalid');
    const helperId = field.dataset.errorHelperId;
    if (!helperId) return;
    const helper = document.getElementById(helperId);
    if (helper) {
      helper.textContent = '';
      helper.hidden = true;
    }
  }

  function setFieldError(field, message) {
    if (!field) return;
    field.setAttribute('aria-invalid', 'true');

    let helper = null;
    const existingHelperId = field.dataset.errorHelperId;
    if (existingHelperId) {
      helper = document.getElementById(existingHelperId);
    }
    if (!helper) {
      helper = document.createElement('p');
      helper.className = 'muted';
      helper.setAttribute('data-role', 'field-error');
      helper.setAttribute('aria-live', 'polite');
      helper.id = `${field.form?.id || 'form'}-${field.name || 'field'}-error`;
      field.dataset.errorHelperId = helper.id;
      field.insertAdjacentElement('afterend', helper);
    }

    helper.hidden = false;
    helper.textContent = message;
    field.setAttribute('aria-describedby', helper.id);
  }

  function clearFormErrors(form) {
    if (!form) return;
    for (const field of form.querySelectorAll('[aria-invalid="true"]')) {
      clearFieldError(field);
    }
  }

  function validateDateRange(form, startFieldName = 'date_from', endFieldName = 'date_to') {
    const startField = form.elements.namedItem(startFieldName);
    const endField = form.elements.namedItem(endFieldName);
    clearFieldError(startField);
    clearFieldError(endField);

    const startValue = String(startField?.value || '').trim();
    const endValue = String(endField?.value || '').trim();

    if (!startValue || !endValue) return true;

    const startDate = new Date(startValue);
    const endDate = new Date(endValue);
    if (startDate.getTime() > endDate.getTime()) {
      setFieldError(startField, 'Start date must be on or before end date.');
      setFieldError(endField, 'End date must be on or after start date.');
      return false;
    }

    return true;
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
      updateLiveStatus(new Date());
    } catch (_error) {
      updateLiveStatus();
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
      showFeedback(filtersFeedback, 'Result deleted successfully.', 'success', 3000);
    } catch (_error) {
      showFeedback(filtersFeedback, 'Could not delete result. Please retry.', 'error');
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
      showFeedback(filtersFeedback, `Device ${serial} deleted successfully.`, 'success', 3000);
    } catch (_error) {
      showFeedback(filtersFeedback, 'Could not delete device. Please retry.', 'error');
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
    clearFormErrors(filtersForm);
    clearFeedback(filtersFeedback);
    if (!validateDateRange(filtersForm)) {
      showFeedback(filtersFeedback, 'Please fix the date range before applying filters.', 'error');
      return;
    }
    paginationState.latestStatus.currentPage = 1;
    paginationState.recentFailures.currentPage = 1;
    refreshDashboard();
    showFeedback(filtersFeedback, 'Filters applied.', 'success', 2500);
  });

  syncLiveControls();
  updateLiveStatus();
  startRefreshTimer();
  refreshDashboard();
  attachDismissHandlers();

  if (liveUpdatesEnabledInput) {
    liveUpdatesEnabledInput.addEventListener('change', () => {
      livePreferences.enabled = liveUpdatesEnabledInput.checked;
      saveLivePreferences(livePreferences);
      syncLiveControls();
      updateLiveStatus();
      startRefreshTimer();
      if (livePreferences.enabled) {
        refreshDashboard();
      }
    });
  }

  if (liveUpdatesIntervalSelect) {
    liveUpdatesIntervalSelect.addEventListener('change', () => {
      livePreferences.intervalMs = parseIntervalMs(liveUpdatesIntervalSelect.value);
      saveLivePreferences(livePreferences);
      syncLiveControls();
      updateLiveStatus();
      startRefreshTimer();
      if (livePreferences.enabled) {
        refreshDashboard();
      }
    });
  }

  if (openExportDialogButton && exportDialog && exportDialogForm) {
    openExportDialogButton.addEventListener('click', () => {
      clearFormErrors(exportDialogForm);
      clearFeedback(exportFeedback);
      exportDialog.showModal();
    });
    if (exportNavLink) {
      exportNavLink.addEventListener('click', (event) => {
        event.preventDefault();
        clearFormErrors(exportDialogForm);
        clearFeedback(exportFeedback);
        exportDialog.showModal();
      });
    }
    if (cancelExportButton) {
      cancelExportButton.addEventListener('click', () => exportDialog.close());
    }
    exportDialogForm.addEventListener('submit', (event) => {
      event.preventDefault();
      clearFormErrors(exportDialogForm);
      clearFeedback(exportFeedback);

      if (!validateDateRange(exportDialogForm)) {
        showFeedback(exportFeedback, 'Date range is invalid. Update dates and try again.', 'error');
        return;
      }

      const params = new URLSearchParams();
      const formData = new FormData(exportDialogForm);
      for (const [key, value] of formData.entries()) {
        if (value) params.set(key, String(value));
      }
      if (!formData.has('include_csv')) params.set('include_csv', 'false');
      if (!formData.has('include_certificates')) params.set('include_certificates', 'false');
      const organizationField = exportDialogForm.elements.namedItem('organization');
      const organization = params.get('organization');
      if (!organization) {
        setFieldError(organizationField, 'Select an organization to export.');
        showFeedback(exportFeedback, 'Please choose an organization to export.', 'error');
        return;
      }

      showFeedback(exportFeedback, 'Starting ZIP export…', 'success', 2500);
      window.location.href = `/export.zip?${params.toString()}`;
      exportDialog.close();
    });
  }

  if (openPrintDialogButton && printDialog && printDialogForm) {
    openPrintDialogButton.addEventListener('click', () => {
      clearFormErrors(printDialogForm);
      clearFeedback(printFeedback);
      printDialog.showModal();
    });
    if (cancelPrintButton) {
      cancelPrintButton.addEventListener('click', () => printDialog.close());
    }
    printDialogForm.addEventListener('submit', (event) => {
      event.preventDefault();
      clearFormErrors(printDialogForm);
      clearFeedback(printFeedback);
      const params = new URLSearchParams();
      const formData = new FormData(printDialogForm);
      for (const [key, value] of formData.entries()) {
        if (value) params.set(key, String(value));
      }
      if (!formData.has('include_csv')) params.set('include_csv', 'false');
      if (!formData.has('include_certificates')) params.set('include_certificates', 'false');
      const organizationField = printDialogForm.elements.namedItem('organization');
      const organization = params.get('organization');
      if (!organization) {
        setFieldError(organizationField, 'Select an organization to print.');
        showFeedback(printFeedback, 'Please choose an organization to print.', 'error');
        return;
      }

      showFeedback(printFeedback, 'Opening print view…', 'success', 2500);
      window.open(`/print-report?${params.toString()}`, '_blank', 'noopener');
      printDialog.close();
    });
  }

  if (openImportDialogButton && importDialog && importDialogForm) {
    openImportDialogButton.addEventListener('click', () => {
      clearFormErrors(importDialogForm);
      clearFeedback(importOnceFeedback);
      importDialog.showModal();
    });

    if (cancelImportButton) {
      cancelImportButton.addEventListener('click', () => importDialog.close());
    }

    importDialogForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearFormErrors(importDialogForm);
      clearFeedback(importOnceFeedback);
      const formData = new FormData(importDialogForm);
      const folderField = importDialogForm.elements.namedItem('folder_path');
      const folderPath = String(formData.get('folder_path') || '').trim();
      if (!folderPath) {
        setFieldError(folderField, 'Enter a folder path to import.');
        showFeedback(importOnceFeedback, 'Please provide a folder path.', 'error');
        return;
      }

      showFeedback(importOnceFeedback, 'Importing folder…', 'success');
      try {
        const response = await fetch(`/api/import-folder-once?folder_path=${encodeURIComponent(folderPath)}`, {
          method: 'POST'
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || 'Import failed');
        }
        showFeedback(importOnceFeedback, `Imported ${payload.processed}/${payload.total} files from ${payload.folder}. Failed: ${payload.failed}.`, 'success', 5000);
        await refreshDashboard();
      } catch (error) {
        showFeedback(importOnceFeedback, `Import failed: ${error.message}`, 'error');
      }
    });
  }
})();
