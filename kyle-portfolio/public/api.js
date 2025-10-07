const runtimeBase = (typeof window !== 'undefined' && (window.LEGEND_API_URL || window.NEXT_PUBLIC_API_BASE))
  || (typeof process !== 'undefined' && process.env && (process.env.NEXT_PUBLIC_API_BASE || process.env.LEGEND_API_URL))
  || '';

const apiBase = runtimeBase.replace(/\/$/, '');

function buildUrl(route) {
  if (!route) {
    return apiBase || '';
  }
  if (typeof route === 'string' && /^(https?:)?\/\//i.test(route)) {
    return route;
  }
  const normalizedRoute = route.startsWith('/') ? route : `/${route}`;
  return `${apiBase}${normalizedRoute}`;
}

function withAcceptHeader(init = {}) {
  const headers = new Headers(init.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  return { ...init, headers };
}

export async function api(route, init) {
  const url = buildUrl(route);
  const response = await fetch(url, withAcceptHeader(init));

  if (!response.ok) {
    let bodyText = '';
    try {
      bodyText = await response.text();
    } catch (err) {
      bodyText = '';
    }
    const error = new Error(`Legend API request failed (${response.status} ${response.statusText})`);
    error.status = response.status;
    error.statusText = response.statusText;
    error.url = url;
    error.body = bodyText;
    throw error;
  }

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json();
  } else if (response.status !== 204) {
    data = await response.text();
  }

  return {
    data,
    status: response.status,
    headers: response.headers,
    url,
  };
}

export { apiBase };
