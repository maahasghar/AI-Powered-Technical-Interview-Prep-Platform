import { act, render, screen } from "@testing-library/react";
import { api } from "./api";
import { useResource } from "./ui";

jest.mock("./api", () => ({ api: jest.fn() }));
function Result({ path = "/submissions/1" }) {
  const { data, loading, error } = useResource(path, true);
  return <p>{loading ? "loading" : error || data.status}</p>;
}
beforeEach(() => { jest.useFakeTimers(); api.mockReset(); });
afterEach(() => { jest.useRealTimers(); });

test("polls queued and running submissions and stops at a terminal state", async () => {
  api.mockResolvedValueOnce({ status: "QUEUED" })
    .mockResolvedValueOnce({ status: "RUNNING" })
    .mockResolvedValueOnce({ status: "PASSED" });
  await act(async () => { render(<Result />); });
  expect(screen.getByText("QUEUED")).toBeInTheDocument();
  await act(async () => { jest.advanceTimersByTime(2000); });
  expect(screen.getByText("RUNNING")).toBeInTheDocument();
  await act(async () => { jest.advanceTimersByTime(2000); });
  expect(screen.getByText("PASSED")).toBeInTheDocument();
  await act(async () => { jest.advanceTimersByTime(10000); });
  expect(api).toHaveBeenCalledTimes(3);
});
test("unmount cancels polling and aborts the request", async () => {
  api.mockResolvedValue({ status: "QUEUED" });
  let view;
  await act(async () => { view = render(<Result />); });
  const signal = api.mock.calls[0][1].signal;
  view.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => { jest.advanceTimersByTime(10000); });
  expect(api).toHaveBeenCalledTimes(1);
});
test("polling errors are shown and do not cause an uncontrolled retry loop", async () => {
  api.mockResolvedValueOnce({ status: "QUEUED" }).mockRejectedValueOnce(new Error("Offline"));
  await act(async () => { render(<Result />); });
  await act(async () => { jest.advanceTimersByTime(2000); });
  expect(screen.getByText("Offline")).toBeInTheDocument();
  await act(async () => { jest.advanceTimersByTime(10000); });
  expect(api).toHaveBeenCalledTimes(2);
});
