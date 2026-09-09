import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  Difficulty,
  ErrorMessage,
  pretty,
  ResourceState,
  useResource,
} from "../ui";
function Editor({ problem }) {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/submissions", {
        method: "POST",
        body: { problem_id: problem.id, code, language },
      });
      navigate(`/submissions/${result.id}`);
    } catch (failure) {
      setError(failure.message);
      setBusy(false);
    }
  }
  return (
    <form className="panel editor" onSubmit={submit}>
      <div className="editor-heading">
        <h2>Your solution</h2>
        <label>
          Language
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
        </label>
      </div>
      <label className="code-label" htmlFor="code">
        Code
      </label>
      <textarea
        id="code"
        className="code-editor"
        spellCheck="false"
        required
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Write your solution here…"
      />
      <ErrorMessage>{error}</ErrorMessage>
      <div className="editor-footer">
        <span className="muted">Your attempt will be saved to history.</span>
        <button
          className="primary"
          disabled={busy || !code.trim() || !problem.is_active}
        >
          {busy ? "Submitting…" : "Submit solution"}
        </button>
      </div>
    </form>
  );
}
export default function ProblemDetail() {
  const { problemId } = useParams();
  const resource = useResource(`/problems/${encodeURIComponent(problemId)}`);
  if (resource.loading || resource.error)
    return <ResourceState resource={resource} />;
  const problem = resource.data;
  return (
    <>
      <Link to="/problems">← All problems</Link>
      <div className="page-heading">
        <h1>{problem.title}</h1>
        <Difficulty value={problem.difficulty} />
      </div>
      {!problem.is_active && (
        <p className="error">
          This problem is archived and cannot accept submissions.
        </p>
      )}
      <div className="workspace">
        <section className="panel description">
          <p className="eyebrow">Problem brief</p>
          <p className="prose">{problem.description}</p>
          <div className="tags">
            {problem.categories.map((category) => (
              <span className="badge" key={category}>
                {category}
              </span>
            ))}
          </div>
          <h2>Test cases</h2>
          <pre>{pretty(problem.test_cases)}</pre>
        </section>
        <Editor key={problem.id} problem={problem} />
      </div>
    </>
  );
}
