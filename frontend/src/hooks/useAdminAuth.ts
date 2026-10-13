import { useCallback, useState } from "react";
import * as api from "../api/client";
import * as customerApi from "../api/customer";

const STORAGE_KEY = "aria_admin_key";
// Shared with hooks/useCustomerAuth.ts -- deliberately not re-exported
// from there, so this stays the one place that reads a customer session
// to decide admin-screen access, the same way app/api/deps.py's
// get_admin_principal is the one backend place that does it.
const CUSTOMER_TOKEN_KEY = "aria_user_session";
const CUSTOMER_CREDENTIAL_PREFIX = "cust:";

export type PrincipalKind = "admin" | "customer" | null;

/** The admin screen (Agents, Sessions, Leads, Customers, Tools,
 * Knowledge) now has two different ways in, matching the backend's
 * `app/api/deps.py::Principal`:
 *
 * - The platform operator logs in here directly (`login()` below) with
 *   the shared admin key, and sees every agent on the platform.
 * - A self-serve customer logs in at /login (useCustomerAuth) and is
 *   recognized here automatically -- their session token (read straight
 *   out of the same localStorage key useCustomerAuth uses) is wrapped as
 *   `"cust:" + token` and carried as `adminKey` through every existing
 *   admin API call unchanged (see api/client.ts::authHeaders). Every
 *   list/detail view they see comes back pre-scoped to only the agents
 *   they created -- enforced server-side, not just hidden in this UI.
 *
 * If a platform-admin key is present, it always wins (there's no
 * legitimate case where a browser would have both, but precedence is
 * explicit rather than accidental). */
export function useAdminAuth() {
  const [storedAdminKey, setStoredAdminKey] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [customerToken] = useState<string | null>(() => localStorage.getItem(CUSTOMER_TOKEN_KEY));
  const [error, setError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const principalKind: PrincipalKind = storedAdminKey ? "admin" : customerToken ? "customer" : null;
  const adminKey = storedAdminKey || (customerToken ? `${CUSTOMER_CREDENTIAL_PREFIX}${customerToken}` : null);

  const login = useCallback(async (username: string, password: string) => {
    setLoggingIn(true);
    setError(null);
    try {
      const { admin_key } = await api.adminLogin(username, password);
      localStorage.setItem(STORAGE_KEY, admin_key);
      setStoredAdminKey(admin_key);
      return true;
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Could not sign in.");
      return false;
    } finally {
      setLoggingIn(false);
    }
  }, []);

  const logout = useCallback(() => {
    if (customerToken) customerApi.logout(customerToken).catch(() => {});
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(CUSTOMER_TOKEN_KEY);
    localStorage.removeItem("aria_user_profile");
    setStoredAdminKey(null);
  }, [customerToken]);

  return { adminKey, principalKind, isAuthenticated: !!adminKey, login, logout, error, loggingIn };
}
