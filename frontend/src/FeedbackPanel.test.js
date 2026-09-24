import { act, fireEvent, render, screen } from "@testing-library/react";
import FeedbackPanel from "./FeedbackPanel";
import { api } from "./api";

jest.mock("./api", () => ({ api: jest.fn() }));
beforeEach(() => { api.mockReset(); });

test("solution generation requires an explicit Show solution click", async () => {
  api.mockResolvedValue({ eligible: true, items: [{ id: 1, stage: "DIAGNOSIS", status: "READY", feedback: {
    strengths: ["Problem category: arrays."], likely_issue: null, hint: null,
    complexity: { time: "O(n)", space: "O(1)" }, next_step: "Keep testing.",
  } }] });
  render(<FeedbackPanel submissionId={9} />);
  await screen.findByText("Problem category: arrays.");
  expect(api.mock.calls.every(call => call[1]?.method !== "POST")).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Show solution" }));
  await act(async () => {});
  expect(api).toHaveBeenCalledWith("/submissions/9/feedback", { method: "POST", body: { action: "show_solution" } });
});

test("second hint stays disabled until first feedback is ready", async () => {
  api.mockResolvedValue({ eligible: true, items: [{ id: 1, stage: "DIAGNOSIS", status: "FAILED", error: "Unavailable" }] });
  render(<FeedbackPanel submissionId={9} />);
  await screen.findByText("Unavailable");
  expect(screen.getByRole("button", { name: "Second hint" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Retry first feedback" })).toBeEnabled();
});

test("coaching failure is separate from the judge result", async () => {
  api.mockRejectedValue(new Error("PRIVATE PROVIDER ERROR"));
  render(<FeedbackPanel submissionId={9} />);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Your judge result is unchanged");
  expect(alert).toHaveTextContent("PRIVATE PROVIDER ERROR");
});

test("suggested solution renders explicit source inside a code block", async () => {
  api.mockResolvedValue({ eligible: true, items: [{ id: 3, stage: "SOLUTION", status: "READY", feedback: {
    strengths: ["Readable implementation."], likely_issue: null, hint: null,
    complexity: { time: "O(1)", space: "O(1)" }, next_step: "Return the constant.",
    solution_code: "def solve():\n    return 1",
  } }] });
  render(<FeedbackPanel submissionId={9} />);
  const code = await screen.findByText(/def solve\(\):/);
  expect(code.tagName).toBe("CODE");
  expect(code.parentElement).toHaveClass("code-block");
  expect(screen.getByText("Return the constant.")).toBeInTheDocument();
});

test("missing solution code shows a retry instead of a suggested solution", async () => {
  api.mockResolvedValue({ eligible: true, items: [{ id: 3, stage: "SOLUTION", status: "FAILED", feedback: null,
    error: "A code solution could not be generated. Retry show solution.",
  }] });
  render(<FeedbackPanel submissionId={9} />);
  const retry = await screen.findByRole("button", { name: "Retry show solution" });
  expect(screen.queryByText("Suggested solution")).not.toBeInTheDocument();
  fireEvent.click(retry);
  await act(async () => {});
  expect(api).toHaveBeenCalledWith("/submissions/9/feedback", { method: "POST", body: { action: "show_solution" } });
});
