// src/pages/SignIn.tsx
import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../services/api";

const SignIn: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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

  return isAuthReady && isLoggedIn ? (
    <Navigate to="/" replace />
  ) : (
    <div className="auth-animated-page flex min-h-screen items-center justify-center px-4 py-24 sm:px-6 lg:px-8">
      <div className="auth-aurora" />
      <div className="auth-grid" />
      <div className="auth-orb auth-orb-one" />
      <div className="auth-orb auth-orb-two" />
      <div className="auth-orb auth-orb-three" />
      <div className="auth-ring auth-ring-one" />
      <div className="auth-ring auth-ring-two" />
      <div className="auth-symbol auth-symbol-one">♡</div>
      <div className="auth-symbol auth-symbol-two">✦</div>
      <div className="auth-symbol auth-symbol-three">♡</div>
      <div className="auth-symbol auth-symbol-four">✧</div>

      <Link to="/#home" className="absolute left-5 top-5 z-10 flex items-center gap-3 font-bold text-[#633449] sm:left-10 sm:top-7">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#b95777] to-[#71384e] text-white shadow-[0_13px_30px_rgba(128,54,78,0.19)]">Q</span>
        <span>Qubool Match</span>
      </Link>
      <Link to="/#home" className="absolute right-5 top-8 z-10 hidden text-sm font-semibold text-[#7c5a62] hover:text-[#b95777] sm:block">
        ← Back to home
      </Link>

      <div className="auth-enter relative z-[2] grid w-full max-w-5xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="hidden px-4 text-[#563442] lg:block">
          <span className="inline-flex rounded-full border border-white/70 bg-white/55 px-4 py-2 text-xs font-extrabold uppercase tracking-[0.18em] text-[#8c3d5b] shadow-[0_12px_30px_rgba(112,53,75,0.07)]">
            Private • Verified • Meaningful
          </span>
          <h1 className="mt-5 font-heading text-6xl font-bold leading-[0.96] tracking-[-0.04em] text-[#3c2731]">
            Continue with <span className="text-[#b95777]">trust.</span>
          </h1>
          <p className="mt-5 max-w-md leading-7 text-[#705f5b]">
            Your matches, preferences, and conversations are waiting in a calmer, more intentional space.
          </p>
        </aside>

        <section className="auth-card-glass relative w-full rounded-[2rem] p-6 sm:p-8">
          <div className="mb-6 text-center">
            <div className="auth-bob mx-auto mb-4 grid h-16 w-16 place-items-center rounded-[1.35rem] bg-gradient-to-br from-[#b95777] to-[#7b3d54] text-2xl font-black text-white shadow-[0_16px_34px_rgba(135,52,78,0.19)]">
              Q
            </div>
            <h2 className="font-heading text-4xl font-bold text-[#3b2731]">Welcome back</h2>
            <p className="mt-2 text-sm text-[#7c6b67]">Sign in to continue your match journey.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signin-email">Email address</label>
              <div className="relative">
                <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#a9808a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4h16v16H4z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m4 7 8 6 8-6" />
                </svg>
                <input
                  id="signin-email"
                  type="email"
                  className="auth-input auth-input-with-icon"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signin-password">Password</label>
              <div className="relative">
                <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#a9808a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10V7a4 4 0 018 0v3" />
                </svg>
                <input
                  id="signin-password"
                  type={showPassword ? "text" : "password"}
                  className="auth-input auth-input-with-icon pr-16"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-[#8b7178] hover:text-[#b95777]">
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>
            
            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            )}
            
            <div className="flex items-center justify-between gap-3 text-sm text-[#786966]">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded accent-[#b95777]" />
                Remember me
              </label>
              <a href="#" className="font-bold text-[#9d3d5e] hover:underline">Forgot password?</a>
            </div>

            <button type="submit" disabled={loading} className="auth-submit w-full rounded-2xl bg-gradient-to-r from-[#b95777] to-[#7b3d54] px-5 py-4 font-bold text-white disabled:cursor-not-allowed disabled:opacity-70">
              <span className="relative z-[1]">{loading ? "Signing In..." : "Sign In"}</span>
            </button>

            <div className="grid grid-cols-[2.25rem_1fr] items-center gap-3 rounded-2xl bg-[#f8ece7] p-3 text-sm text-[#6d5e5a]">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-[#9d3d5e]">◇</span>
              <span><b className="block text-[#5b3444]">Secure access</b>Your profile and preferences stay protected.</span>
            </div>
          </form>

          <p className="mt-6 text-center text-sm text-[#71635f]">
            Don't have an account?{" "}
            <Link to="/signup" className="font-bold text-[#9d3d5e] hover:underline">
              Create your profile
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
};

export default SignIn;
