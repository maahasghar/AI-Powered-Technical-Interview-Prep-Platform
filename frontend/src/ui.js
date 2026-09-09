import { useEffect, useState } from "react";
import { api } from "./api";
export function useResource(path) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: "" });
    api(path)
      .then((data) => {
        if (active) setState({ data, loading: false, error: "" });
      })
      .catch((error) => {
        if (active)
          setState({ data: null, loading: false, error: error.message });
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { ...state, reload: () => setVersion((value) => value + 1) };
}
export function ErrorMessage({ children }) {
  return children ? (
    <p role="alert" className="error">
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
  return (
    <span className={`badge ${value === "accepted" ? "difficulty-1" : ""}`}>
      {(value || "pending").replaceAll("_", " ")}
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
