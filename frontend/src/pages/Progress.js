import { ResourceState, useResource } from "../ui";

function rate(value) {
  return `${Math.round(value * 100)}%`;
}

function Breakdown({ title, values }) {
  const entries = Object.entries(values);
  return (
    <section className="progress-section" aria-labelledby={`${title}-heading`}>
      <h2 id={`${title}-heading`}>{title}</h2>
      {entries.length === 0 ? <p className="muted">No data yet.</p> : (
        <div className="progress-list">
          {entries.map(([name, bucket]) => (
            <div className="progress-row" key={name}>
              <strong>{name}</strong>
              <span>{bucket.solved} solved / {bucket.attempted} attempted</span>
              <span>{rate(bucket.solve_rate)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function Progress() {
  const resource = useResource("/users/me/progress");
  if (resource.loading || resource.error) return <ResourceState resource={resource} />;
  const progress = resource.data;
  return (
    <>
      <p className="eyebrow">Your practice record</p>
      <h1>Progress</h1>
      <p className="muted">A clear view of the problems you have attempted and solved.</p>
      <section className="progress-summary" aria-label="Progress summary">
        <div className="progress-stat"><strong>{progress.total_attempted}</strong><span>Attempted</span></div>
        <div className="progress-stat"><strong>{progress.total_solved}</strong><span>Solved</span></div>
        <div className="progress-stat"><strong>{rate(progress.solve_rate)}</strong><span>Success rate</span></div>
      </section>
      <div className="progress-grid">
        <Breakdown title="By difficulty" values={progress.by_difficulty} />
        <Breakdown title="By category" values={progress.by_category} />
      </div>
      <section className="panel" aria-labelledby="recent-activity-heading">
        <h2 id="recent-activity-heading">Recent activity</h2>
        {progress.recent_activity.length === 0 ? <p className="empty">Submit a solution to start building your progress.</p> : (
          <ul className="activity-list">
            {progress.recent_activity.map((item, index) => (
              <li key={`${item.created_at}-${index}`}>
                <span>{item.status.replaceAll("_", " ")}</span>
                <time dateTime={item.created_at || undefined}>
                  {item.created_at ? new Date(item.created_at).toLocaleString() : "Date unavailable"}
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}