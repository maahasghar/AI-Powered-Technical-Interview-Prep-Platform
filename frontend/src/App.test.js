import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth";
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
  if (authenticated)
    sessionStorage.setItem(
      "interview-session",
      JSON.stringify({ access_token: "access", refresh_token: "refresh" }),
    );
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
  global.fetch = jest.fn();
});
afterEach(() => {
  jest.restoreAllMocks();
});
test("protected deep link returns to the editor after login and submits code", async () => {
  global.fetch.mockImplementation((url) => {
    if (url.endsWith("/auth/login"))
      return response({ access_token: "access", refresh_token: "refresh" });
    if (url.endsWith("/problems/1")) return response(problem);
    if (url.endsWith("/submissions")) return response({ id: 9 });
    if (url.endsWith("/submissions/9"))
      return response({
        id: 9,
        problem_id: 1,
        code: "print(1)",
        language: "python",
        status: "pending",
        result: null,
      });
    throw new Error(`Unexpected URL ${url}`);
  });
  open("/problems/1/editor");
  expect(
    screen.getByRole("heading", { name: "Welcome back" }),
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
    screen.getByText(/Evaluation results are not available yet/),
  ).toBeInTheDocument();
  const submissionCall = global.fetch.mock.calls.find(([url]) =>
    url.endsWith("/submissions"),
  );
  expect(JSON.parse(submissionCall[1].body)).toEqual({
    problem_id: 1,
    code: "print(1)",
    language: "python",
  });
  expect(submissionCall[1].headers.Authorization).toBe("Bearer access");
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
      { id: 8, problem_id: 1, language: "python", status: "accepted" },
    ],
  });
  open("/history", true);
  expect(await screen.findByRole("link", { name: "#8" })).toHaveAttribute(
    "href",
    "/submissions/8",
  );
  expect(screen.getByText("accepted")).toBeInTheDocument();
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
  expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
    token: "reset-token",
    new_password: "newpassword",
  });
});
test("missing verification token prevents submission", () => {
  open("/verify-email");
  expect(screen.getByRole("button", { name: "Verify email" })).toBeDisabled();
  expect(global.fetch).not.toHaveBeenCalled();
});
test("unknown route shows not found", () => {
  open("/does-not-exist");
  expect(
    screen.getByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});
