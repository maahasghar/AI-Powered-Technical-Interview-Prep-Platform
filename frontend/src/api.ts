const BASE = (process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export interface User {
  id: number;
  email: string;
  role: string;
  is_verified: boolean;
}
interface Tokens { access_token: string; token_type: string }
export interface Problem {
  id: number; title: string; difficulty: number; categories: string[];
  description: string; test_cases: string; is_active: boolean;
}
export interface SubmissionInput { problem_id: number; code: string; language?: string }
export interface Submission extends SubmissionInput {
  id: number; user_id: number; language: string; status: string;
  result: string | null; created_at: string | null; updated_at: string | null;
}
interface Message { message: string }
interface Registration { email: string; password: string; full_name?: string | null; bio?: string | null; avatar_url?: string | null }
type WithQuery<P extends string> = P | `${P}?${string}`;
type GetPath = "/users/me" | WithQuery<"/problems"> | `/problems/${number}` |
  WithQuery<"/submissions/me"> | `/submissions/${number}` | `/auth/verify-email?token=${string}`;
type GetResponse<P extends GetPath> = P extends "/users/me" ? User :
  P extends WithQuery<"/problems"> ? Problem[] : P extends `/problems/${number}` ? Problem :
  P extends WithQuery<"/submissions/me"> ? Submission[] : P extends `/submissions/${number}` ? Submission : Message;
interface PostBodies {
  "/submissions": SubmissionInput;
  "/auth/register": Registration;
  "/auth/forgot-password": { email: string };
  "/auth/resend-verification": { email: string };
  "/auth/reset-password": { token: string; new_password: string };
}
type PostResponse<P extends keyof PostBodies> = P extends "/submissions" ? Submission :
  P extends "/auth/register" ? { id: number; email: string; is_verified: boolean } : Message;
type Options = Omit<RequestInit, "body"> & { body?: unknown };
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
let accessToken: string | null = null;
let user: User | null = null;
let generation = 0;
const listeners = new Set<() => void>();
export const getCurrentUser = () => user;
export function subscribeAuth(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function clearAuthentication() {
  generation++;
  accessToken = null;
  user = null;
  listeners.forEach(listener => listener());
}
function publishUser(value: User) {
  user = value;
  listeners.forEach(listener => listener());
}
async function request<T>(path: string, options: Options = {}, token: string | null = null): Promise<T> {
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Invalid API path");
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-Session-Request", "1");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${BASE}${path}`, {
    ...options, credentials: "include", headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new ApiError(Array.isArray(detail)
      ? detail.map((item: { msg: string }) => item.msg).join(". ")
      : typeof detail === "string" ? detail : "Request failed. Please try again.", response.status);
  }
  return data as T;
}
function validateTokens(value: Tokens): string {
  if (!value || typeof value.access_token !== "string" || !value.access_token || value.token_type !== "bearer")
    throw new Error("Invalid authentication response");
  return value.access_token;
}
function validateUser(value: User): User {
  if (!value || !Number.isInteger(value.id) || typeof value.email !== "string" ||
      typeof value.role !== "string" || typeof value.is_verified !== "boolean")
    throw new Error("Invalid user response");
  return value;
}
// Serialize cookie mutations so a late refresh cannot replace a login/logout cookie.
let sessionQueue: Promise<unknown> = Promise.resolve();
function serialize<T>(operation: () => Promise<T>): Promise<T> {
  const coordinated = () => typeof navigator !== "undefined" && navigator.locks
    ? navigator.locks.request("interview-auth-cookie", operation)
    : operation();
  const pending = sessionQueue.then(coordinated, coordinated);
  sessionQueue = pending.catch(() => undefined);
  return pending;
}
let refreshing: { generation: number; promise: Promise<void> } | null = null;
export function refresh(): Promise<void> {
  const epoch = generation;
  if (refreshing?.generation === epoch) return refreshing.promise;
  const promise = serialize(async () => {
    if (epoch !== generation) throw new Error("Session changed");
    try {
      const token = validateTokens(await request<Tokens>("/auth/refresh", { method: "POST" }));
      if (epoch !== generation) throw new Error("Session changed");
      accessToken = token;
    } catch (error) {
      if (epoch === generation) clearAuthentication();
      throw error;
    }
  });
  refreshing = { generation: epoch, promise };
  void promise.finally(() => {
    if (refreshing?.promise === promise) refreshing = null;
  }).catch(() => undefined);
  return promise;
}
export function api<P extends GetPath>(path: P, options?: Omit<Options, "method" | "body"> & { method?: "GET" }, authenticated?: boolean): Promise<GetResponse<P>>;
export function api<P extends keyof PostBodies>(path: P, options: Omit<Options, "method" | "body"> & { method: "POST"; body: PostBodies[P] }, authenticated?: boolean): Promise<PostResponse<P>>;
export async function api<T = unknown>(path: string, options: Options = {}, authenticated = true): Promise<T> {
  const epoch = generation;
  const token = authenticated ? accessToken : null;
  try { return await request<T>(path, options, token); }
  catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !authenticated || epoch !== generation) throw error;
    // Another request may already have refreshed this token.
    if (!accessToken || accessToken === token) await refresh();
    if (epoch !== generation) throw error;
    try { return await request<T>(path, options, accessToken); }
    catch (retryError) {
      if (retryError instanceof ApiError && retryError.status === 401 && epoch === generation) clearAuthentication();
      throw retryError;
    }
  }
}
export async function currentUser(): Promise<User> {
  const epoch = generation;
  const value = validateUser(await api("/users/me"));
  if (epoch !== generation) throw new Error("Session changed");
  publishUser(value);
  return value;
}
export async function login(email: string, password: string): Promise<void> {
  clearAuthentication();
  const epoch = generation;
  try {
    await serialize(async () => {
      if (epoch !== generation) throw new Error("Session changed");
      const token = validateTokens(await request<Tokens>("/auth/login", { method: "POST", body: { email, password } }));
      if (epoch !== generation) throw new Error("Session changed");
      accessToken = token;
    });
    await currentUser();
  } catch (error) {
    if (epoch === generation) clearAuthentication();
    throw error;
  }
}
let restoration: Promise<void> | null = null;
export function restoreSession(): Promise<void> {
  if (restoration) return restoration;
  // Remove credentials persisted by previous versions. New credentials stay in memory.
  try { sessionStorage.removeItem("interview-session"); } catch { /* Storage may be disabled. */ }
  const pending = (async () => {
    const epoch = generation;
    try { await refresh(); await currentUser(); }
    catch { if (epoch === generation) clearAuthentication(); }
  })();
  restoration = pending;
  void pending.finally(() => { if (restoration === pending) restoration = null; });
  return pending;
}
export async function logout(): Promise<void> {
  clearAuthentication();
  await serialize(() => request("/auth/logout", { method: "POST" }));
}
