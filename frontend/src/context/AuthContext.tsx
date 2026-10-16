import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { UserProfile, UserRole } from '../types';
import { apiFetch, setCsrfToken } from '../api/client';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  authError: string | null;
  loginWithRole: (role: UserRole, organizationId?: string) => Promise<boolean>;
  loginWithOidc: () => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const fetchCsrf = useCallback(async () => {
    try {
      const res = await apiFetch('http://localhost:8000/api/auth/csrf');
      if (res.ok) {
        const data = await res.json();
        setCsrfToken(data.csrf_token);
      }
    } catch {
      // Non-blocking error if CSRF fetch fails
    }
  }, []);

  const refreshSession = useCallback(async () => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await apiFetch('http://localhost:8000/api/auth/me');
      if (res.ok) {
        const profile: UserProfile = await res.json();
        setUser(profile);
        await fetchCsrf();
      } else {
        setUser(null);
        setCsrfToken(null);
      }
    } catch (err: any) {
      setUser(null);
      setCsrfToken(null);
    } finally {
      setIsLoading(false);
    }
  }, [fetchCsrf]);

  useEffect(() => {
    refreshSession();

    const handleUnauthorized = () => {
      setUser(null);
      setCsrfToken(null);
    };

    window.addEventListener('medrule:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('medrule:unauthorized', handleUnauthorized);
    };
  }, [refreshSession]);

  const loginWithRole = async (role: UserRole, organizationId = 'org_riverside'): Promise<boolean> => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await apiFetch('http://localhost:8000/api/auth/dev-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, organization_id: organizationId }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detail = errData.detail || 'Sign-in failed. Please check server configuration.';
        setAuthError(detail);
        setIsLoading(false);
        return false;
      }

      const profile: UserProfile = await res.json();
      setUser(profile);
      await fetchCsrf();
      setIsLoading(false);
      return true;
    } catch (err: any) {
      setAuthError(err.message || 'Network error connecting to MedRule authentication service.');
      setIsLoading(false);
      return false;
    }
  };

  const loginWithOidc = async (): Promise<void> => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await apiFetch('http://localhost:8000/api/auth/login-url');
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Identity Provider service is unavailable.');
      }
      const data = await res.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err: any) {
      setAuthError(err.message || 'Failed to initiate OIDC Authorization Code Flow.');
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await apiFetch('http://localhost:8000/api/auth/logout', { method: 'POST' });
    } catch {
      // Proceed with local logout regardless of network response
    } finally {
      setUser(null);
      setCsrfToken(null);
      setIsLoading(false);
    }
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    return user.permissions.includes(permission);
  };

  const hasRole = (roles: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const allowed = Array.isArray(roles) ? roles : [roles];
    return allowed.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        authError,
        loginWithRole,
        loginWithOidc,
        logout,
        refreshSession,
        hasPermission,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
