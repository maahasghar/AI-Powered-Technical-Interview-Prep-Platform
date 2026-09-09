const BASE = (
  process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");
const KEY = "interview-session";
export function getSession() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}
export function setSession(session) {
  if (session) sessionStorage.setItem(KEY, JSON.stringify(session));
  else sessionStorage.removeItem(KEY);
  window.dispatchEvent(new Event("session-change"));
}
let refreshing;
async function request(path, options = {}, token) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const detail = data?.detail;
    const error = new Error(
      Array.isArray(detail)
        ? detail.map((item) => item.msg).join(". ")
        : detail || "Request failed. Please try again.",
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
export async function api(path, options = {}, authenticated = true) {
  const session = authenticated ? getSession() : null;
  try {
    return await request(path, options, session?.access_token);
  } catch (error) {
    if (error.status !== 401 || !authenticated) throw error;
    if (!session?.refresh_token) {
      setSession(null);
      throw error;
    }
    if (!refreshing) {
      refreshing = request("/auth/refresh", {
        method: "POST",
        body: { refresh_token: session.refresh_token },
      })
        .then((tokens) => {
          if (getSession()?.refresh_token === session.refresh_token)
            setSession(tokens);
          return tokens;
        })
        .catch((failure) => {
          if (failure.status === 401) setSession(null);
          throw failure;
        })
        .finally(() => {
          refreshing = null;
        });
    }
    const tokens = await refreshing;
    if (!getSession()) throw error;
    return request(path, options, tokens.access_token);
  }
}
