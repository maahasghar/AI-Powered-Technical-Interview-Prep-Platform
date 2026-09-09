import { useState } from "react";
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
} from "react-router-dom";
import { AuthProvider, ProtectedRoute, useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import Problems from "./pages/Problems";
import ProblemDetail from "./pages/ProblemDetail";
import { History, SubmissionResult } from "./pages/Submissions";
import { ErrorMessage } from "./ui";
import "./App.css";
function Layout() {
  const { session, logout } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function signOut() {
    setBusy(true);
    setError("");
    try {
      await logout();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <header className="site-header">
        <Link className="brand" to="/problems">
          <span className="brand-icon">&gt;_</span> Interview Prep
        </Link>
        <nav aria-label="Main navigation">
          {session ? (
            <>
              <NavLink to="/problems">Problems</NavLink>
              <NavLink to="/history">History</NavLink>
              <button disabled={busy} onClick={signOut}>
                {busy ? "Signing out…" : "Sign out"}
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Sign in</NavLink>
              <Link className="button primary" to="/register">
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>
      <main>
        <ErrorMessage>{error}</ErrorMessage>
        <Outlet />
      </main>
      <footer>Small steps. Stronger solutions.</footer>
    </>
  );
}
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/problems" replace />} />
        {[
          "login",
          "register",
          "forgot-password",
          "reset-password",
          "verify-email",
          "resend-verification",
        ].map((mode) => (
          <Route
            key={mode}
            path={mode}
            element={<AuthPage key={mode} mode={mode} />}
          />
        ))}
        <Route element={<ProtectedRoute />}>
          <Route path="problems" element={<Problems />} />
          <Route path="problems/:problemId" element={<ProblemDetail />} />
          <Route
            path="problems/:problemId/editor"
            element={<ProblemDetail />}
          />
          <Route
            path="submissions/:submissionId"
            element={<SubmissionResult />}
          />
          <Route path="history" element={<History />} />
        </Route>
        <Route
          path="*"
          element={
            <section className="panel empty">
              <h1>Page not found</h1>
              <Link to="/problems">Back to problems</Link>
            </section>
          }
        />
      </Route>
    </Routes>
  );
}
export default function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
