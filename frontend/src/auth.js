import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import * as client from "./api";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(client.getCurrentUser);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    const unsubscribe = client.subscribeAuth(() => setUser(client.getCurrentUser()));
    client.restoreSession().finally(() => { if (active) setLoading(false); });
    return () => { active = false; unsubscribe(); };
  }, []);
  return (
    <AuthContext.Provider value={{ user, loading, login: client.login, logout: client.logout,
      refresh: client.refresh, currentUser: client.currentUser }}>
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth requires AuthProvider");
  return context;
}
export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p role="status">Restoring session…</p>;
  return user ? <Outlet /> : <Navigate to="/login"
    state={{ from: location.pathname + location.search }} replace />;
}
