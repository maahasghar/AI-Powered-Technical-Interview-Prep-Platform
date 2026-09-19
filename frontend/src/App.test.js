import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth";
import { clearAuthentication } from "./api";
const problem = {
  id: 1,
  title: "Pair Sum",
  difficulty: 1,
  categories: ["arrays"],
  description: "Find two indices.",
  test_cases: "[]",
  is_active: true,
};
function response(data, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => data });
}
function open(path, authenticated = false) {
  const handler = global.fetch;
  global.fetch = jest.fn((url, options) => {
    if (url.endsWith("/feedback")) return response({ eligible: false, items: [] });
    if (url.endsWith("/auth/refresh")) return authenticated
      ? response({ access_token: "access", token_type: "bearer" })
      : response({ detail: "Unauthorized" }, 401);
    if (url.endsWith("/users/me")) return response({ id: 1, email: "user@example.com", role: "user", is_verified: true });
    return handler(url, options);
  });
  return render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  sessionStorage.clear();
  clearAuthentication();
  global.fetch = jest.fn();
});
afterEach(() => {
  jest.restoreAllMocks();
});
test("protected deep link returns to the editor after login and submits code", async () => {
  global.fetch.mockImplementation((url) => {
    if (url.endsWith("/auth/login"))
      return response({ access_token: "access", token_type: "bearer" });
    if (url.endsWith("/problems/1")) return response(problem);
    if (url.endsWith("/submissions")) return response({ id: 9 });
    if (url.endsWith("/submissions/9"))
      return response({
        id: 9,
        problem_id: 1,
        code: "print(1)",
        language: "python",
        status: "QUEUED",
        result: null,
      });
    throw new Error(`Unexpected URL ${url}`);
  });
  open("/problems/1/editor");
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "user@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Pair Sum" });
  fireEvent.change(screen.getByLabelText("Code"), {
    target: { value: "print(1)" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Submit solution" }));
  await screen.findByRole("heading", { name: "Submission #9" });
  expect(
    screen.getByText(/Results update automatically/),
  ).toBeInTheDocument();
  const submissionCall = global.fetch.mock.calls.find(([url]) =>
    url.endsWith("/submissions"),
  );
  expect(JSON.parse(submissionCall[1].body)).toEqual({
    problem_id: 1,
    code: "print(1)",
    language: "python",
  });
  expect(submissionCall[1].headers.get("Authorization")).toBe("Bearer access");
});
test("browsing applies difficulty filters and links to a problem", async () => {
  global.fetch.mockImplementation(() => response([problem]));
  open("/problems", true);
  expect(await screen.findByRole("link", { name: /Pair Sum/ })).toHaveAttribute(
    "href",
    "/problems/1",
  );
  fireEvent.change(screen.getByLabelText("Difficulty"), {
    target: { value: "2" },
  });
  await waitFor(() =>
    expect(
      global.fetch.mock.calls.some(([url]) => url.includes("difficulty=2")),
    ).toBe(true),
  );
});
test("history links to result and displays backend status", async () => {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [
      { id: 8, problem_id: 1, language: "python", status: "PASSED" },
    ],
  });
  open("/history", true);
  expect(await screen.findByRole("link", { name: "#8" })).toHaveAttribute(
    "href",
    "/submissions/8",
  );
  expect(screen.getByText("Passed")).toBeInTheDocument();
});
test("failed requests show retry and recover", async () => {
  global.fetch
    .mockImplementationOnce(() =>
      response({ detail: "Service unavailable" }, 503),
    )
    .mockImplementation(() => response([]));
  open("/problems", true);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Service unavailable",
  );
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText(/No problems found/)).toBeInTheDocument();
});
test("registration explains verification and does not log in", async () => {
  global.fetch.mockImplementation(() =>
    response({ id: 1, is_verified: false }, 201),
  );
  open("/register");
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "user@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Check your email",
  );
  expect(sessionStorage.getItem("interview-session")).toBeNull();
});
test("reset link uses token and new_password contract", async () => {
  global.fetch.mockImplementation(() =>
    response({ message: "Password reset successfully" }),
  );
  open("/reset-password?token=reset-token");
  fireEvent.change(screen.getByLabelText("New password"), {
    target: { value: "newpassword" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByRole("status");
  expect(JSON.parse(global.fetch.mock.calls.find(([url]) => url.endsWith("/auth/reset-password"))[1].body)).toEqual({
    token: "reset-token",
    new_password: "newpassword",
  });
});
test("missing verification token prevents submission", async () => {
  await act(async () => { open("/verify-email"); });
  expect(screen.getByRole("button", { name: "Verify email" })).toBeDisabled();
  expect(global.fetch.mock.calls.every(([url]) => url.endsWith("/auth/refresh"))).toBe(true);
});
test("unknown route shows not found", async () => {
  await act(async () => { open("/does-not-exist"); });
  expect(
    screen.getByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});
test("protected routes wait for startup restoration before rendering", async () => {
  let finishRefresh;
  global.fetch.mockImplementation(url => {
    if (url.endsWith("/auth/refresh")) return new Promise(resolve => { finishRefresh = resolve; });
    if (url.endsWith("/users/me")) return response({ id: 1, email: "user@example.com", role: "user", is_verified: true });
    return response([problem]);
  });
  render(<MemoryRouter initialEntries={["/problems"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AuthProvider><AppRoutes /></AuthProvider>
  </MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("Restoring session");
  expect(screen.queryByRole("heading", { name: "Welcome back" })).not.toBeInTheDocument();
  await act(async () => {
    await Promise.resolve();
    finishRefresh(await response({ access_token: "restored", token_type: "bearer" }));
  });
  expect(await screen.findByRole("link", { name: /Pair Sum/ })).toBeInTheDocument();
});
test("startup with an invalid cookie redirects a protected route to login", async () => {
  global.fetch.mockImplementation(() => response({ detail: "Unauthorized" }, 401));
  render(<MemoryRouter initialEntries={["/history"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AuthProvider><AppRoutes /></AuthProvider>
  </MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  expect(global.fetch.mock.calls).toHaveLength(1);
});

test("submission results render only candidate fields", async () => {
  global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({
    id: 9, problem_id: 1, language: "python", code: "def solve(): pass", status: "FAILED",
    result: { message: "Your solution did not pass all tests.", tests_passed: 1,
      tests_total: 3, runtime_ms: 12.5, memory_bytes: 1048576,
      diagnostics: "HIDDEN_SENTINEL", hidden_tests: ["HIDDEN_SENTINEL"] },
  }) });
  open("/submissions/9", true);
  expect(await screen.findByText("Your solution did not pass all tests.")).toBeInTheDocument();
  expect(screen.getByText("1 / 3")).toBeInTheDocument();
  expect(screen.getByText("12.5 ms")).toBeInTheDocument();
  expect(screen.getByText("1.00 MiB (sampled)")).toBeInTheDocument();
  expect(screen.queryByText(/HIDDEN_SENTINEL/)).not.toBeInTheDocument();
});
