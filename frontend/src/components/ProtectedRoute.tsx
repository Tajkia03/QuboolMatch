import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isLoggedIn, isAuthReady } = useAuth();
  const location = useLocation();

  // For development, allow access to FindMatches, NIDVerification, and Notifications
  // without requiring authentication
  if (
    location.pathname === '/find-matches' || 
    location.pathname === '/notifications' || 
    location.pathname === '/nid-verification'
  ) {
    return <>{children}</>;
  }

  if (!isAuthReady) {
    return null;
  }

  if (!isLoggedIn) {
    // Redirect to the signin page if not authenticated
    return <Navigate to="/signin" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
