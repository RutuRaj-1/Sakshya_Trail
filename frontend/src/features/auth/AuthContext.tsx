import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '@/api/endpoints';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session via /auth/me
  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.me();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string): Promise<User> => {
    const res = await authApi.login({ email, password });
    setUser(res.user);
    return res.user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      sessionStorage.removeItem('dismiss_password_rotation');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: null,
      isLoading: false,
      isAuthenticated: false,
      login: async () => {
        throw new Error('AuthProvider is required for authentication operations');
      },
      logout: async () => {},
      refreshUser: async () => {},
    };
  }
  return context;
}
