import { useEffect, useState } from "react";
import { api } from "./api";
export function useResource(path, pollSubmission = false) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    let timer;
    const controller = new AbortController();
    setState({ data: null, loading: true, error: "" });
    async function load() {
      try {
        const data = await api(path, { signal: controller.signal });
        if (!active) return;
        setState({ data, loading: false, error: "" });
        if (pollSubmission && ["QUEUED", "RUNNING"].includes(data.status)) {
          timer = setTimeout(load, 2000);
        }
      } catch (error) {
        if (active) setState(previous => ({ ...previous, loading: false, error: error.message }));
      }
    }
    load();
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [path, version, pollSubmission]);
  return { ...state, reload: () => setVersion((value) => value + 1) };
}
export function ErrorMessage({ children }) {
  return children ? (
    <p role="alert" aria-live="assertive" className="error">
      {children}
    </p>
  ) : null;
}
export function Loading() {
  return (
    <p role="status" className="muted">
      Loading…
    </p>
  );
}
export function ResourceState({ resource }) {
  return resource.loading ? (
    <Loading />
  ) : (
    <>
      <ErrorMessage>{resource.error}</ErrorMessage>
      <button onClick={resource.reload}>Try again</button>
    </>
  );
}
export function Difficulty({ value }) {
  return (
    <span className={`badge difficulty-${value}`}>
      {["", "Easy", "Medium", "Hard"][value] || "Unknown"}
    </span>
  );
}
export function Status({ value }) {
  const label = {
    PASSED: "Passed",
    FAILED: "Failed",
    RUNTIME_ERROR: "Runtime error",
    TIME_LIMIT_EXCEEDED: "Time limit exceeded",
    QUEUED: "Queued",
    RUNNING: "Running",
  }[value] || "Unknown";
  return (
    <span className={`badge ${value === "PASSED" ? "difficulty-1" : ""}`}>
      {label}
    </span>
  );
}
export function pretty(value) {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}
export function Pagination({ page, count, onChange }) {
  return (
    <div className="pagination">
      <button disabled={page === 0} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span>Page {page + 1}</span>
      <button disabled={count < 20} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </div>
  );
}
