import { useCallback, useEffect, useState } from "react";
import * as api from "../api/customer";
import type { CustomerUser } from "../types";

const TOKEN_KEY = "aria_user_session";
const USER_KEY = "aria_user_profile";

export function useCustomerAuth() {
  const [sessionToken, setSessionToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<CustomerUser | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    try {
      return raw ? (JSON.parse(raw) as CustomerUser) : null;
    } catch {
      return null;
    }
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const persist = useCallback((token: string, u: CustomerUser) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    setSessionToken(token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    if (sessionToken) api.logout(sessionToken).catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setSessionToken(null);
    setUser(null);
  }, [sessionToken]);

  // If a stored token has expired/been revoked server-side, fail closed
  // the next time we'd otherwise rely on it, rather than showing stale
  // "logged in" UI against a session that no longer works.
  useEffect(() => {
    if (!sessionToken) return;
    api.me(sessionToken).catch(() => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setSessionToken(null);
      setUser(null);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signup = useCallback(
    async (payload: { email: string; password: string; name: string; company_name?: string }) => {
      setBusy(true);
      setError(null);
      try {
        const result = await api.signup(payload);
        persist(result.session_token, result.user);
        return true;
      } catch (err) {
        setError(err instanceof api.ApiError ? err.message : "Could not create your account.");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [persist]
  );

  const login = useCallback(
    async (email: string, password: string) => {
      setBusy(true);
      setError(null);
      try {
        const result = await api.login(email, password);
        persist(result.session_token, result.user);
        return true;
      } catch (err) {
        setError(err instanceof api.ApiError ? err.message : "Could not sign in.");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [persist]
  );

  return { sessionToken, user, isAuthenticated: !!sessionToken, signup, login, logout, error, busy };
}
