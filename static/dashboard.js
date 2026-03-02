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
    if (!value) {
      return '-';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

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
        <td>${formatDate(failure.tested_at)}</td>
        <td class="fail">${failure.result}</td>
      `;

      recentFailuresTableBody.appendChild(row);
    }
  }

  async function refreshDashboard() {
    const query = getQueryString();
    const endpoint = query ? `/api/dashboard?${query}` : '/api/dashboard';

    try {
      const response = await fetch(endpoint, { headers: { Accept: 'application/json' } });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

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

  setInterval(refreshDashboard, pollIntervalMs);
  refreshDashboard();

  if (openExportDialogButton && exportDialog && exportDialogForm) {
    openExportDialogButton.addEventListener('click', () => {
      exportDialog.showModal();
    });

    if (exportNavLink) {
      exportNavLink.addEventListener('click', (event) => {
        event.preventDefault();
        exportDialog.showModal();
      });
    }

    if (cancelExportButton) {
      cancelExportButton.addEventListener('click', () => {
        exportDialog.close();
      });
    }

    exportDialogForm.addEventListener('submit', (event) => {
      event.preventDefault();

      const params = new URLSearchParams();
      const formData = new FormData(exportDialogForm);

      for (const [key, value] of formData.entries()) {
        if (value) {
          params.set(key, String(value));
        }
      }

      if (!formData.has('include_csv')) {
        params.set('include_csv', 'false');
      }
      if (!formData.has('include_certificates')) {
        params.set('include_certificates', 'false');
      }

      const organization = params.get('organization');
      if (!organization) {
        alert('Please choose an organization to export.');
        return;
      }

      window.location.href = `/export.zip?${params.toString()}`;
      exportDialog.close();
    });
  }
})();
