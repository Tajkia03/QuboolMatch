// src/pages/SignIn.tsx
import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../services/api";
import { Button, Input, Card } from "../components/ui";

const SignIn: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login, isLoggedIn, isAuthReady } = useAuth();

  useEffect(() => {
    if (isAuthReady && isLoggedIn) {
      navigate("/", { replace: true });
    }
  }, [isAuthReady, isLoggedIn, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Call backend API for sign in
      const response = await fetch(`${API_BASE_URL}/auth/sign_in`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to sign in");
      }

      const data = await response.json();
      
      // Use the login function from AuthContext
      login(data.access_token);
      
      // Navigate to home page after successful sign in
      navigate("/", { replace: true });
    } catch (err) {
      console.error("Sign in error:", err);
      setError(err instanceof Error ? err.message : "An error occurred during sign in");
    } finally {
      setLoading(false);
    }
  };

  return (
    isAuthReady && isLoggedIn ? (
      <Navigate to="/" replace />
    ) : (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-600 to-accent-600 rounded-2xl shadow-lg mb-4">
            <span className="text-white font-bold text-2xl">Q</span>
          </div>
          <h2 className="text-3xl font-heading font-bold bg-gradient-to-r from-primary-700 to-accent-700 bg-clip-text text-transparent">
            Welcome Back
          </h2>
          <p className="mt-2 text-gray-600">
            Sign in to continue your journey
          </p>
        </div>

        {/* Sign In Card */}
        <Card className="animate-slide-up" padding="lg">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Input */}
            <Input
              type="email"
              label="Email Address"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                </svg>
              }
            />

            {/* Password Input */}
            <Input
              type="password"
              label="Password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              }
            />
            
            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded-lg animate-scale-in">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-red-700 text-sm font-medium">{error}</span>
                </div>
              </div>
            )}
            
            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={loading}
              className="w-full"
            >
              {loading ? "Signing In..." : "Sign In"}
            </Button>

            {/* Forgot Password Link */}
            <div className="text-center">
              <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                Forgot your password?
              </a>
            </div>
          </form>
        </Card>

        {/* Sign Up Link */}
        <p className="text-center text-gray-600 mt-6 animate-fade-in">
          Don't have an account?{" "}
          <Link to="/signup" className="text-primary-600 hover:text-primary-700 font-semibold">
            Sign Up
          </Link>
        </p>
      </div>
    </div>
    )
  );
};

export default SignIn;
