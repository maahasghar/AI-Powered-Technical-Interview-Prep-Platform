import { Link, useSearchParams } from "react-router-dom";
import { Difficulty, Pagination, ResourceState, useResource } from "../ui";
export default function Problems() {
  const [params, setParams] = useSearchParams();
  const difficulty = params.get("difficulty") || "";
  const category = params.get("category") || "";
  const page = Math.max(0, Number.parseInt(params.get("page"), 10) || 0);
  const query = new URLSearchParams({ skip: page * 20, limit: 20 });
  if (difficulty) query.set("difficulty", difficulty);
  if (category) query.set("category", category);
  const resource = useResource(`/problems?${query}`);
  function filter(key, value) {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    next.delete("page");
    setParams(next);
  }
  return (
    <>
      <p className="eyebrow">The practice room</p>
      <h1>Find your next challenge.</h1>
      <p className="muted">
        Explore problems, sharpen your thinking, and make every attempt count.
      </p>
      <section className="panel">
        <div className="filters">
          <label>
            Difficulty
            <select
              value={difficulty}
              onChange={(e) => filter("difficulty", e.target.value)}
            >
              <option value="">All difficulties</option>
              <option value="1">Easy</option>
              <option value="2">Medium</option>
              <option value="3">Hard</option>
            </select>
          </label>
          <label>
            Category
            <input
              placeholder="e.g. arrays"
              value={category}
              onChange={(e) => filter("category", e.target.value)}
            />
          </label>
        </div>
        {resource.loading || resource.error ? (
          <ResourceState resource={resource} />
        ) : (
          <>
            {resource.data.length === 0 ? (
              <p className="empty">No problems found. Try another filter.</p>
            ) : (
              <div className="problem-list">
                {resource.data.map((problem) => (
                  <Link
                    className="problem-row"
                    key={problem.id}
                    to={`/problems/${problem.id}`}
                  >
                    <div>
                      <h2>{problem.title}</h2>
                      <p className="muted">{problem.categories.join(" · ")}</p>
                    </div>
                    <Difficulty value={problem.difficulty} />
                    <span aria-hidden="true">↗</span>
                  </Link>
                ))}
              </div>
            )}
            <Pagination
              page={page}
              count={resource.data.length}
              onChange={(value) => {
                const next = new URLSearchParams(params);
                next.set("page", value);
                setParams(next);
              }}
            />
          </>
        )}
      </section>
    </>
  );
}
