import { useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorMessage } from "../ui";
const titles = {
  login: "Welcome back",
  register: "Create your account",
  "forgot-password": "Reset your password",
  "reset-password": "Choose a new password",
  "verify-email": "Verify your email",
  "resend-verification": "Resend verification",
};
export default function AuthPage({ mode }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const token = params.get("token");
  const needsToken = ["reset-password", "verify-email"].includes(mode);
  const hasPassword = ["login", "register", "reset-password"].includes(mode);
  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
        const target = location.state?.from;
        navigate(
          target?.startsWith("/") && !target.startsWith("//")
            ? target
            : "/problems",
          { replace: true },
        );
      } else if (mode === "verify-email") {
        const result = await api(
          `/auth/verify-email?token=${encodeURIComponent(token)}`,
          {},
          false,
        );
        setMessage(result.message);
      } else {
        const body =
          mode === "reset-password"
            ? { token, new_password: password }
            : mode === "register"
              ? { email, password, full_name: name || null }
              : { email };
        const result = await api(
          `/auth/${mode}`,
          { method: "POST", body },
          false,
        );
        setMessage(
          mode === "register"
            ? "Account created. Check your email to verify your account before signing in."
            : result.message,
        );
      }
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <section className="auth-intro">
        <p className="eyebrow">Practice with purpose</p>
        <h1>Your next chapter starts with practice.</h1>
        <p>
          Build confidence, one problem at a time. Write solutions and keep
          track of your progress.
        </p>
      </section>
      <section className="panel auth-card">
        <h2>{titles[mode]}</h2>
        <p className="muted">A little progress, every day.</p>
        <ErrorMessage>{error}</ErrorMessage>
        {message ? (
          <p role="status" className="success">
            {message}
          </p>
        ) : (
          <form onSubmit={submit}>
            {needsToken && !token && (
              <ErrorMessage>
                This link is missing its token. Request a new email below.
              </ErrorMessage>
            )}
            {mode === "register" && (
              <label>
                Full name
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </label>
            )}
            {!needsToken && (
              <label>
                Email
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </label>
            )}
            {hasPassword && (
              <label>
                {mode === "reset-password" ? "New password" : "Password"}
                <input
                  type="password"
                  required
                  minLength={mode === "login" ? 1 : 8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                />
              </label>
            )}
            <button
              className="primary"
              disabled={busy || (needsToken && !token)}
            >
              {busy
                ? "Please wait…"
                : mode === "login"
                  ? "Sign in"
                  : mode === "register"
                    ? "Create account"
                    : mode === "verify-email"
                      ? "Verify email"
                      : "Continue"}
            </button>
          </form>
        )}
        <div className="auth-links">
          <Link to="/login">Sign in</Link>
          <Link to="/register">Create account</Link>
          <Link to="/forgot-password">Forgot password?</Link>
          <Link to="/resend-verification">Resend verification</Link>
        </div>
      </section>
    </div>
  );
}
