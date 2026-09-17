import FeedbackPanel from "../FeedbackPanel";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Pagination, ResourceState, Status, useResource } from "../ui";
export function History() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(0, Number.parseInt(params.get("page"), 10) || 0);
  const resource = useResource(`/submissions/me?skip=${page * 20}&limit=20`);
  return (
    <>
      <p className="eyebrow">Every attempt counts</p>
      <h1>Submission history</h1>
      <p className="muted">Revisit your solutions and see where you stand.</p>
      <section className="panel">
        {resource.loading || resource.error ? (
          <ResourceState resource={resource} />
        ) : (
          <>
            {resource.data.length === 0 ? (
              <div className="empty">
                <h2>No submissions yet</h2>
                <p>Choose a problem and take your first step.</p>
                <Link to="/problems">Browse problems →</Link>
              </div>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Submission</th>
                      <th>Problem</th>
                      <th>Language</th>
                      <th>Status</th>
                      <th>Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resource.data.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <Link to={`/submissions/${item.id}`}>#{item.id}</Link>
                        </td>
                        <td>
                          <Link to={`/problems/${item.problem_id}`}>
                            Problem #{item.problem_id}
                          </Link>
                        </td>
                        <td>{item.language}</td>
                        <td>
                          <Status value={item.status} />
                        </td>
                        <td>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleString()
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Pagination
              page={page}
              count={resource.data.length}
              onChange={(value) => setParams({ page: value })}
            />
          </>
        )}
      </section>
    </>
  );
}
export function SubmissionResult() {
  const { submissionId } = useParams();
  const resource = useResource(
    `/submissions/${encodeURIComponent(submissionId)}`,
    true,
  );
  if (resource.loading || resource.error)
    return <ResourceState resource={resource} />;
  const submission = resource.data;
  const pending = ["QUEUED", "RUNNING"].includes(submission.status);
  return (
    <>
      <Link to="/history">← Submission history</Link>
      <div className="page-heading">
        <h1>Submission #{submission.id}</h1>
        <Status value={submission.status} />
      </div>
      <section className="panel">
        <div className="result-meta">
          <Link to={`/problems/${submission.problem_id}`}>
            Problem #{submission.problem_id}
          </Link>
          <span>{submission.language}</span>
          <button onClick={resource.reload}>Refresh status</button>
        </div>
        <h2>Result</h2>
        {submission.result ? (
          <div>
            <p role="status">{submission.result.message}</p>
            <dl>
              <dt>Tests passed</dt>
              <dd>{submission.result.tests_passed != null && submission.result.tests_total != null
                ? `${submission.result.tests_passed} / ${submission.result.tests_total}` : "Unavailable"}</dd>
              <dt>Runtime</dt>
              <dd>{submission.result.runtime_ms != null ? `${submission.result.runtime_ms.toFixed(1)} ms` : "Unavailable"}</dd>
              <dt>Memory usage</dt>
              <dd>{submission.result.memory_bytes != null ? `${(submission.result.memory_bytes / 1024 / 1024).toFixed(2)} MiB (sampled)` : "Unavailable"}</dd>
            </dl>
          </div>
        ) : (
          <p role="status" className="muted">
            {pending
              ? "Your submission is being evaluated. Results update automatically."
              : "No result details are available."}
          </p>
        )}
        <h2>Submitted code</h2>
        <pre className="submitted-code">{submission.code}</pre>
      </section>
      {!pending && <FeedbackPanel key={submission.id} submissionId={submission.id} />}
    </>
  );
}
