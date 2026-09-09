import { api, getSession, setSession } from "./api";
const response = (data, status = 200) =>
  Promise.resolve({ ok: status < 400, status, json: async () => data });
beforeEach(() => {
  sessionStorage.clear();
  global.fetch = jest.fn();
});
test("concurrent unauthorized requests share one rotating token refresh", async () => {
  setSession({ access_token: "old", refresh_token: "refresh" });
  global.fetch.mockImplementation((url, options) => {
    if (url.endsWith("/auth/refresh"))
      return response({ access_token: "new", refresh_token: "rotated" });
    return options.headers.Authorization === "Bearer old"
      ? response({ detail: "Expired" }, 401)
      : response([]);
  });
  await Promise.all([api("/problems"), api("/submissions/me")]);
  expect(
    global.fetch.mock.calls.filter(([url]) => url.endsWith("/auth/refresh")),
  ).toHaveLength(1);
  expect(getSession().refresh_token).toBe("rotated");
});
test("invalid refresh clears session", async () => {
  setSession({ access_token: "old", refresh_token: "invalid" });
  global.fetch.mockImplementation(() =>
    response({ detail: "Invalid token" }, 401),
  );
  await expect(api("/problems")).rejects.toThrow("Invalid token");
  expect(getSession()).toBeNull();
});
