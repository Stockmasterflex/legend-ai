// Compatibility shim: injects the modern module bundle while keeping legacy entrypoint.
(function loadModernDashboard() {
  if (document.querySelector('script[data-legend-app="module"]')) {
    return;
  }

  const moduleScript = document.createElement('script');
  moduleScript.type = 'module';
  moduleScript.src = 'app.js';
  moduleScript.dataset.legendApp = 'module';
  document.head.appendChild(moduleScript);
})();
