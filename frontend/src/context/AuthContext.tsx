import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';

interface AuthContextType {
  isLoggedIn: boolean;
  isAuthReady: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

const ACCESS_TOKEN_KEY = 'accessToken';

const getStoredToken = (): string | null => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

const isJwtStillValid = (token: string | null): boolean => {
  if (!token) {
    return false;
  }

  const parts = token.split('.');
  if (parts.length !== 3) {
    return false;
  }

  try {
    const payloadJson = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson) as { exp?: number };
    if (typeof payload.exp !== 'number') {
      return true;
    }

    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => isJwtStillValid(getStoredToken()));
  const [isAuthReady, setIsAuthReady] = useState<boolean>(false);

  useEffect(() => {
    const token = getStoredToken();
    setIsLoggedIn(isJwtStillValid(token));
    setIsAuthReady(true);

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key !== ACCESS_TOKEN_KEY) {
        return;
      }

      setIsLoggedIn(isJwtStillValid(event.newValue));
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const login = (token: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
    setIsLoggedIn(isJwtStillValid(token));
    setIsAuthReady(true);
  };

  const logout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setIsLoggedIn(false);
    setIsAuthReady(true);
  };

  const value = {
    isLoggedIn,
    isAuthReady,
    login,
    logout
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
