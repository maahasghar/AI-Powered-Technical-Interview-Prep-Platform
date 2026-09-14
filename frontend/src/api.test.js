import { api, clearAuthentication, getCurrentUser, login, logout, restoreSession } from "./api";
const user = { id: 1, email: "user@example.com", role: "user", is_verified: true };
const response = (data, status = 200) => Promise.resolve({ ok: status < 400, status, json: async () => data });
const tokens = (token) => ({ access_token: token, token_type: "bearer" });
beforeEach(() => {
  clearAuthentication();
  sessionStorage.clear();
  global.fetch = jest.fn();
});
async function signIn() {
  global.fetch.mockImplementation(url => response(url.endsWith("/users/me") ? user : tokens("old")));
  await login("user@example.com", "password");
  global.fetch.mockClear();
}
test("startup restores cookie session and loads current user without persisted tokens", async () => {
  sessionStorage.setItem("interview-session", "old credentials");
  global.fetch.mockImplementation(url => response(url.endsWith("/users/me") ? user : tokens("new")));
  await restoreSession();
  expect(getCurrentUser()).toEqual(user);
  expect(sessionStorage.getItem("interview-session")).toBeNull();
  expect(global.fetch.mock.calls[0][1].credentials).toBe("include");
  expect(global.fetch.mock.calls[0][1].body).toBeUndefined();
  expect(global.fetch.mock.calls[1][1].headers.get("Authorization")).toBe("Bearer new");
});
test("concurrent unauthorized requests share one refresh", async () => {
  await signIn();
  global.fetch.mockImplementation((url, options) => {
    if (url.endsWith("/auth/refresh")) return response(tokens("new"));
    return options.headers.get("Authorization") === "Bearer old"
      ? response({ detail: "Expired" }, 401) : response([]);
  });
  await Promise.all([api("/problems"), api("/submissions/me")]);
  expect(global.fetch.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
});
test.each([401, 503])("refresh failure (%s) clears authentication", async status => {
  await signIn();
  global.fetch.mockImplementation(url => response({ detail: "Failed" }, url.endsWith("/auth/refresh") ? status : 401));
  await expect(api("/problems")).rejects.toThrow("Failed");
  expect(getCurrentUser()).toBeNull();
});
test("a retried 401 clears authentication without refreshing again", async () => {
  await signIn();
  global.fetch.mockImplementation(url => url.endsWith("/auth/refresh") ? response(tokens("new")) : response({ detail: "Unauthorized" }, 401));
  await expect(api("/problems")).rejects.toThrow("Unauthorized");
  expect(global.fetch).toHaveBeenCalledTimes(3);
  expect(getCurrentUser()).toBeNull();
});
test("public requests do not refresh or attach an access token", async () => {
  await signIn();
  global.fetch.mockImplementation(() => response({ detail: "Invalid" }, 401));
  await expect(api("/auth/login", {}, false)).rejects.toThrow("Invalid");
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(global.fetch.mock.calls[0][1].headers.has("Authorization")).toBe(false);
});
test("logout clears local auth even when the server cannot be reached", async () => {
  await signIn();
  global.fetch.mockRejectedValue(new Error("Offline"));
  await expect(logout()).rejects.toThrow("Offline");
  expect(getCurrentUser()).toBeNull();
});
test("logout during refresh cannot restore authentication or retry the old request", async () => {
  await signIn();
  let finishRefresh;
  global.fetch.mockImplementation(url => {
    if (url.endsWith("/auth/refresh")) return new Promise(resolve => { finishRefresh = resolve; });
    if (url.endsWith("/auth/logout")) return response({ message: "Logged out" });
    return response({ detail: "Expired" }, 401);
  });
  const pending = api("/problems");
  const rejected = expect(pending).rejects.toThrow("Session changed");
  while (!finishRefresh) await Promise.resolve();
  const signedOut = logout();
  finishRefresh(await response(tokens("new")));
  await rejected;
  await signedOut;
  expect(getCurrentUser()).toBeNull();
  expect(global.fetch.mock.calls.filter(([url]) => url.endsWith("/problems"))).toHaveLength(1);
  expect(global.fetch.mock.calls.at(-1)[0]).toMatch(/auth\/logout$/);
});
test("malformed authentication responses are rejected", async () => {
  global.fetch.mockImplementation(() => response({ access_token: 123 }));
  await expect(login("user@example.com", "password")).rejects.toThrow("Invalid authentication response");
  expect(getCurrentUser()).toBeNull();
});
test("a new login wins over an older refresh response", async () => {
  await signIn();
  let finishRefresh;
  global.fetch.mockImplementation(url => {
    if (url.endsWith("/auth/refresh")) return new Promise(resolve => { finishRefresh = resolve; });
    if (url.endsWith("/auth/login")) return response(tokens("different-user"));
    if (url.endsWith("/users/me")) return response({ ...user, id: 2 });
    return response({ detail: "Expired" }, 401);
  });
  const pending = api("/problems");
  const rejected = expect(pending).rejects.toThrow("Session changed");
  while (!finishRefresh) await Promise.resolve();
  const signedIn = login("other@example.com", "password");
  finishRefresh(await response(tokens("stale")));
  await rejected;
  await signedIn;
  expect(getCurrentUser().id).toBe(2);
  const profileCall = global.fetch.mock.calls.find(([url]) => url.endsWith("/users/me"));
  expect(profileCall[1].headers.get("Authorization")).toBe("Bearer different-user");
});
