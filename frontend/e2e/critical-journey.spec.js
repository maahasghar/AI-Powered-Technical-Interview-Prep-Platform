const { test, expect } = require("@playwright/test");

const problem = {
  id: 1,
  title: "Pair Sum",
  difficulty: 1,
  categories: ["arrays"],
  description: "Find two indices whose values add to a target.",
  test_cases: '[{"input":{"nums":[2,7],"target":9},"expected":[0,1]}]',
  is_active: true,
};

async function installJourneyApi(page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const json = (body, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

    if (url.pathname.endsWith("/auth/refresh")) return json({ detail: "Unauthorized" }, 401);
    if (url.pathname.endsWith("/auth/login")) return json({ access_token: "e2e-access", token_type: "bearer" });
    if (url.pathname.endsWith("/users/me")) return json({ id: 1, email: "candidate@example.com", role: "user", is_verified: true });
    if (url.pathname === "/api/v1/problems" && request.method() === "GET") return json([problem]);
    if (url.pathname.endsWith("/problems/1")) return json(problem);
    if (url.pathname === "/api/v1/submissions" && request.method() === "POST") {
      return json({ id: 9, user_id: 1, problem_id: 1, code: "", language: "python", status: "QUEUED", result: null }, 201);
    }
    if (url.pathname.endsWith("/submissions/9/feedback")) {
      return json({
        eligible: true,
        items: [{
          id: 1,
          stage: "DIAGNOSIS",
          status: "READY",
          feedback: {
            strengths: ["The function follows the requested contract."],
            likely_issue: null,
            hint: null,
            complexity: { time: "O(n)", space: "O(n)" },
            next_step: "Keep checking edge cases.",
          },
          error: null,
        }],
      });
    }
    if (url.pathname.endsWith("/submissions/9")) {
      return json({
        id: 9,
        user_id: 1,
        problem_id: 1,
        code: "def solve(nums, target): return [0, 1]",
        language: "python",
        status: "PASSED",
        result: {
          message: "Your solution passed all tests.",
          tests_passed: 1,
          tests_total: 1,
          runtime_ms: 2,
          memory_bytes: 1024,
        },
      });
    }
    if (url.pathname.endsWith("/submissions/me")) {
      return json([{
        id: 9,
        problem_id: 1,
        language: "python",
        status: "PASSED",
        created_at: "2026-09-19T12:00:00Z",
      }]);
    }
    return json({ detail: `Unhandled E2E request: ${request.method()} ${url.pathname}` }, 500);
  });
}

test("candidate can sign in, submit Python, view result, feedback, and history", async ({ page }) => {
  await installJourneyApi(page);
  await page.goto("/login");
  await page.getByLabel("Email").fill("candidate@example.com");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Find your next challenge." })).toBeVisible();
  await page.getByRole("link", { name: /Pair Sum/ }).click();
  await expect(page.getByRole("heading", { name: "Pair Sum" })).toBeVisible();
  await page.getByLabel("Code").fill("def solve(nums, target):\n    return [0, 1]");
  await page.getByRole("button", { name: "Submit solution" }).click();

  await expect(page.getByRole("heading", { name: "Submission #9" })).toBeVisible();
  await expect(page.locator(".page-heading .badge", { hasText: "Passed" })).toBeVisible();
  await expect(page.getByText("The function follows the requested contract.")).toBeVisible();
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "History" }).click();
  await expect(page.getByRole("link", { name: "#9" })).toBeVisible();
  await expect(page.getByRole("row", { name: /#9.*Passed/ })).toBeVisible();
});