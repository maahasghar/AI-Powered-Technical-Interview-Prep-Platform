import { useEffect, useState } from "react";
import { api } from "./api";

const stages = [
  ["DIAGNOSIS", "diagnosis", "First feedback"],
  ["HINT", "hint", "Second hint"],
  ["SOLUTION", "show_solution", "Show solution"],
];

// Splits text on fenced ```code``` blocks so code renders with a monospace background.
function renderWithCodeBlocks(text) {
  const parts = text.split(/```(?:[a-zA-Z0-9]*\n)?([\s\S]*?)```/g);
  return parts.map((part, index) =>
    index % 2 === 1
      ? <pre className="code-block" key={index}><code>{part.trim()}</code></pre>
      : part.trim() && <p key={index}>{part.trim()}</p>
  );
}

export default function FeedbackPanel({ submissionId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    let timer;
    const controller = new AbortController();
    async function load() {
      try {
        const result = await api(`/submissions/${submissionId}/feedback`, { signal: controller.signal });
        if (!active) return;
        if (!Array.isArray(result.items)) throw new Error("Coaching is unavailable.");
        setData(result);
        setError("");
        // The judge may have committed just before its feedback record is created.
        if (result.eligible && (!result.items.length || result.items.some(item => ["QUEUED", "RUNNING"].includes(item.status)))) {
          timer = setTimeout(load, 2000);
        }
        } catch (caught) {
          if (!active || caught?.name === "AbortError") return;
          const detail = caught instanceof Error && caught.message
            ? ` ${caught.message}`
            : " Please check the API connection and try again.";
          setError(`Coaching is unavailable. Your judge result is unchanged.${detail}`);
      }
    }
    load();
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [submissionId, version]);

  async function request(action) {
    setBusy(true);
    setError("");
    try {
      await api(`/submissions/${submissionId}/feedback`, { method: "POST", body: { action } });
      setVersion(value => value + 1);
    } catch {
      setError("Could not request coaching. Your judge result is unchanged.");
    } finally { setBusy(false); }
  }

  const items = data?.items || [];
  const firstReady = items.some(item => item.stage === "DIAGNOSIS" && item.status === "READY");
  return <section className="panel" aria-label="AI coaching">
    <h2>AI coaching</h2>
    <p>Coaching explains possible improvements. The judge result above determines correctness.</p>
    {error && <p role="alert">{error} <button onClick={() => setVersion(value => value + 1)}>Retry coaching</button></p>}
    {!data && !error && <p>Loading coaching…</p>}
    {data && !data.eligible && <p>Coaching requires a completed evaluation with test results.</p>}
    {data?.eligible && stages.map(([stage, action, label]) => {
      const item = items.find(value => value.stage === stage);
      if (item?.status === "READY" && item.feedback) return <div key={stage}>
        <h3>{stage === "SOLUTION" ? "Suggested solution" : label}</h3>
        <ul>
          {item.feedback.strengths.map((strength) => <li key={strength}>{strength}</li>)}
        </ul>
        {item.feedback.likely_issue && <p><strong>Likely issue:</strong> {item.feedback.likely_issue}</p>}
        {item.feedback.hint && <p><strong>Hint:</strong> {item.feedback.hint}</p>}
        {stage === "SOLUTION"
          ? <>
              {item.feedback.solution_code && <pre className="code-block"><code>{item.feedback.solution_code}</code></pre>}
              {renderWithCodeBlocks(item.feedback.next_step)}
              <p><strong>Complexity:</strong> {item.feedback.complexity.time} time, {item.feedback.complexity.space} space</p>
            </>
          : <>
              {stage !== "HINT" && <p><strong>Complexity:</strong> {item.feedback.complexity.time} time, {item.feedback.complexity.space} space</p>}
              <strong>Next step:</strong>
              {renderWithCodeBlocks(item.feedback.next_step)}
            </>}
      </div>;
      if (item && ["QUEUED", "RUNNING"].includes(item.status)) return <p key={stage}>{label}: preparing…</p>;
      return <div key={stage}>
        {item?.status === "FAILED" && <p>{item.error}</p>}
        <button disabled={busy || (stage === "HINT" && !firstReady)} onClick={() => request(action)}>
          {item?.status === "FAILED" ? `Retry ${label.toLowerCase()}` : label}
        </button>
      </div>;
    })}
  </section>;
}
