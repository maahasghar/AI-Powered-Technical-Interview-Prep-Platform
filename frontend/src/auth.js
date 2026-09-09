import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { api, getSession, setSession } from "./api";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [session, updateSession] = useState(getSession);
  useEffect(() => {
    const update = () => updateSession(getSession());
    window.addEventListener("session-change", update);
    return () => window.removeEventListener("session-change", update);
  }, []);
  async function login(email, password) {
    setSession(
      await api(
        "/auth/login",
        { method: "POST", body: { email, password } },
        false,
      ),
    );
  }
  async function logout() {
    const refresh_token = getSession()?.refresh_token;
    if (refresh_token)
      await api(
        "/auth/logout",
        { method: "POST", body: { refresh_token } },
        false,
      );
    setSession(null);
  }
  return (
    <AuthContext.Provider value={{ session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
export function ProtectedRoute() {
  const { session } = useAuth();
  const location = useLocation();
  return session ? (
    <Outlet />
  ) : (
    <Navigate
      to="/login"
      state={{ from: location.pathname + location.search }}
      replace
    />
  );
}
