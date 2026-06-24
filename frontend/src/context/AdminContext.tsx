import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { API_BASE_URL } from '../services/api';

interface AdminContextType {
  isAdminLoggedIn: boolean;
  adminLogin: (token: string) => void;
  adminLogout: () => void;
  isAdmin: boolean;
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

export const useAdmin = () => {
  const context = useContext(AdminContext);
  if (!context) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
};

interface AdminProviderProps {
  children: ReactNode;
}

export const AdminProvider: React.FC<AdminProviderProps> = ({ children }) => {
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState<boolean>(() => {
    return Boolean(sessionStorage.getItem('adminAccessToken'));
  });
  const [isAdmin, setIsAdmin] = useState<boolean>(false);

  useEffect(() => {
    // Check if there's an admin token in the current browser session.
    const adminToken = sessionStorage.getItem('adminAccessToken');
    if (adminToken) {
      // Verify if the token is still valid and user is admin
      verifyAdminToken(adminToken);
    } else {
      setIsAdminLoggedIn(false);
      setIsAdmin(false);
    }
  }, []);

  const verifyAdminToken = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        setIsAdminLoggedIn(true);
        setIsAdmin(true);
      } else {
        // Token is invalid or user is not admin
        sessionStorage.removeItem('adminAccessToken');
        setIsAdminLoggedIn(false);
        setIsAdmin(false);
      }
    } catch (error) {
      // Don't remove token on network errors, just assume not admin for now
      console.error('Error verifying admin token:', error);
      setIsAdminLoggedIn(false);
      setIsAdmin(false);
    }
  };

  const adminLogin = (token: string) => {
    sessionStorage.setItem('adminAccessToken', token);
    setIsAdminLoggedIn(true);
    setIsAdmin(true);
  };

  const adminLogout = () => {
    sessionStorage.removeItem('adminAccessToken');
    setIsAdminLoggedIn(false);
    setIsAdmin(false);
  };

  const value = {
    isAdminLoggedIn,
    adminLogin,
    adminLogout,
    isAdmin
  };

  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
};
