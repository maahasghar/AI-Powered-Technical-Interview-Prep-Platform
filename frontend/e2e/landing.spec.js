const { test, expect } = require("@playwright/test");

for (const width of [360, 768, 1440]) {
  test(`public landing and auth navigation at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/v1/**", route => route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"Unauthorized"}' }));
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Practice technical interviews");
    await expect(page).toHaveURL(/\/$/);
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main")).toBeFocused();
    await expect(page.getByRole("link", { name: "Start Practicing" }).first()).toHaveAttribute("href", "/register");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.getByRole("link", { name: /Take a look inside/ }).click();
    await expect(page.getByText("Illustrative example", { exact: true })).toBeInViewport();
    await page.screenshot({ path: `test-results/landing-${width}.png`, fullPage: true });
    await page.getByRole("link", { name: "Start Practicing" }).last().click();
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await page.getByRole("navigation").getByRole("link", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await page.goto("/history");
    await expect(page).toHaveURL(/\/login$/);
  });
}
