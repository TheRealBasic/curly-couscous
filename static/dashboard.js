(function dashboardPolling() {
  const pollIntervalMs = 3000;
  const filtersForm = document.getElementById('dashboard-filters');
  const totalDevicesValue = document.getElementById('total-devices-value');
  const totalTestsValue = document.getElementById('total-tests-value');
  const failuresLast7DaysValue = document.getElementById('failures-last-7-days-value');
  const latestStatusTableBody = document.getElementById('latest-status-table-body');
  const recentFailuresTableBody = document.getElementById('recent-failures-table-body');
  const liveStatus = document.getElementById('dashboard-live-status');
  const openExportDialogButton = document.getElementById('open-export-dialog');
  const exportDialog = document.getElementById('export-dialog');
  const exportDialogForm = document.getElementById('export-dialog-form');
  const cancelExportButton = document.getElementById('cancel-export');
  const openImportDialogButton = document.getElementById('open-import-dialog');
  const importDialog = document.getElementById('import-dialog');
  const importDialogForm = document.getElementById('import-dialog-form');
  const cancelImportButton = document.getElementById('cancel-import');
  const importOnceStatus = document.getElementById('import-once-status');
  const exportNavLink = document.querySelector('.app-nav__item[href="/export.zip"]');

  if (!filtersForm || !latestStatusTableBody || !recentFailuresTableBody) {
    return;
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

  function updateDevices(devices) {
    latestStatusTableBody.innerHTML = '';
    for (const device of devices) {
      const row = document.createElement('tr');
      const result = device.last_result || 'UNKNOWN';
      row.innerHTML = `
        <td><a href="/device/${device.serial}">${device.serial}</a></td>
        <td>${textOrDash(device.barcode)}</td>
        <td>${textOrDash(device.organization)}</td>
        <td>${textOrDash(device.device_type)}</td>
        <td>${formatDate(device.last_tested_at)}</td>
        <td class="${result.toLowerCase()}">${result}</td>
        <td><button type="button" class="button button-danger js-delete-device" data-serial="${device.serial}">Delete</button></td>
      `;
      latestStatusTableBody.appendChild(row);
    }
  }

  function updateRecentFailures(failures) {
    recentFailuresTableBody.innerHTML = '';
    for (const failure of failures) {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${failure.serial}</td>
        <td>${textOrDash(failure.barcode)}</td>
        <td>${textOrDash(failure.device_type)}</td>
        <td>${textOrDash(failure.fail_reason)}</td>
        <td>${formatDate(failure.tested_at)}</td>
        <td class="fail">${failure.result}</td>
        <td><button type="button" class="button button-danger js-delete-test" data-test-id="${failure.id}">Delete</button></td>
      `;
      recentFailuresTableBody.appendChild(row);
    }
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
      updateDevices(payload.devices || []);
      updateRecentFailures(payload.recent_failures || []);
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
      await refreshDashboard();
    } catch (_error) {
      window.alert('Could not delete device.');
    }
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
