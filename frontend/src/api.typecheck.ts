// Compile-time regression checks. This module is never imported by the app.
import { api, Problem, Submission, User } from "./api";

async function checkContracts() {
  const user: User = await api("/users/me");
  const problems: Problem[] = await api("/problems?limit=20");
  const submission: Submission = await api("/submissions", {
    method: "POST", body: { problem_id: 1, code: "print(1)" },
  });
  // @ts-expect-error Unknown endpoint paths must be rejected.
  await api("/missing-endpoint");
  // @ts-expect-error Submission payloads require code.
  await api("/submissions", { method: "POST", body: { problem_id: 1 } });
  // @ts-expect-error IDs are numeric.
  await api("/submissions", { method: "POST", body: { problem_id: "1", code: "" } });
  // @ts-expect-error Current-user responses are not problem lists.
  const wrong: Problem[] = await api("/users/me");
  return { user, problems, submission, wrong };
}
void checkContracts;
