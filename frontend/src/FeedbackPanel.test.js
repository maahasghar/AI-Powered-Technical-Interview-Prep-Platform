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
  expect(await screen.findByRole("alert")).toHaveTextContent("Your judge result is unchanged");
  expect(screen.queryByText(/PRIVATE PROVIDER/)).not.toBeInTheDocument();
});
