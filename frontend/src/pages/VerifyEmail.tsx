import React, { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../services/api";

const PENDING_SIGNUP_USER_ID_KEY = "pendingSignupUserId";
const PENDING_SIGNUP_EMAIL_KEY = "pendingSignupEmail";
const ONBOARDING_PENDING_KEY = "verificationOnboardingPending";
const SIGNUP_SUCCESS_NOTIFICATION_KEY = "signupSuccessNotification";

const maskEmail = (email: string) => {
  const [localPart, domain] = email.split("@");
  if (!localPart || !domain) {
    return email;
  }

  const visibleStart = localPart.slice(0, Math.min(2, localPart.length));
  const visibleEnd = localPart.length > 4 ? localPart.slice(-1) : "";
  return `${visibleStart}${"*".repeat(Math.max(3, localPart.length - visibleStart.length - visibleEnd.length))}${visibleEnd}@${domain}`;
};

const VerifyEmail: React.FC = () => {
  const navigate = useNavigate();
  const { login, isLoggedIn, isAuthReady } = useAuth();
  const [email, setEmail] = useState("");
  const [userId, setUserId] = useState("");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const maskedEmail = useMemo(() => maskEmail(email), [email]);
  const isPinValid = pin.length === 6;

  useEffect(() => {
    const pendingUserId = sessionStorage.getItem(PENDING_SIGNUP_USER_ID_KEY) || "";
    const pendingEmail = sessionStorage.getItem(PENDING_SIGNUP_EMAIL_KEY) || "";

    if (!pendingUserId || !pendingEmail) {
      navigate("/signup", { replace: true });
      return;
    }

    setUserId(pendingUserId);
    setEmail(pendingEmail);
  }, [navigate]);

  useEffect(() => {
    if (resendCooldown <= 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      setResendCooldown((current) => Math.max(0, current - 1));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [resendCooldown]);

  const handlePinChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setPin(event.target.value.replace(/\D/g, "").slice(0, 6));
    setError("");
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isPinValid) {
      setError("Enter the 6-digit verification PIN.");
      return;
    }

    setLoading(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, email, pin }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.detail || "Failed to verify email.");
      }

      localStorage.setItem(ONBOARDING_PENDING_KEY, "true");
      sessionStorage.setItem(SIGNUP_SUCCESS_NOTIFICATION_KEY, "true");
      sessionStorage.removeItem(PENDING_SIGNUP_USER_ID_KEY);
      sessionStorage.removeItem(PENDING_SIGNUP_EMAIL_KEY);
      login(data.access_token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify email.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || !userId || !email) {
      return;
    }

    setResending(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/resend-email-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, email }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 429 && data?.retry_after_seconds) {
          setResendCooldown(data.retry_after_seconds);
        }
        throw new Error(data?.detail || "Failed to resend verification PIN.");
      }

      setPin("");
      setNotice("A new verification PIN has been sent.");
      setResendCooldown(data?.resend_cooldown_seconds || 60);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend verification PIN.");
    } finally {
      setResending(false);
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
      <Link to="/signup" className="absolute right-5 top-8 z-10 hidden text-sm font-semibold text-[#7c5a62] hover:text-[#b95777] sm:block">
        Back to signup
      </Link>

      <div className="auth-enter relative z-[2] grid w-full max-w-5xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="hidden px-4 text-[#563442] lg:block">
          <span className="inline-flex rounded-full border border-white/70 bg-white/55 px-4 py-2 text-xs font-extrabold uppercase tracking-[0.18em] text-[#8c3d5b] shadow-[0_12px_30px_rgba(112,53,75,0.07)]">
            One more trust step
          </span>
          <h1 className="mt-5 font-heading text-6xl font-bold leading-[0.96] tracking-[-0.04em] text-[#3c2731]">
            Confirm your email, then continue with <span className="text-[#b95777]">verification.</span>
          </h1>
          <p className="mt-5 max-w-md leading-7 text-[#705f5b]">
            This step prepares the account for future email verification without changing your sign up details.
          </p>
        </aside>

        <section className="auth-card-glass relative w-full rounded-[2rem] p-6 sm:p-8">
          <div className="mb-6 text-center">
            <div className="auth-bob mx-auto mb-4 grid h-16 w-16 place-items-center rounded-[1.35rem] bg-gradient-to-br from-[#b95777] to-[#7b3d54] text-2xl font-black text-white shadow-[0_16px_34px_rgba(135,52,78,0.19)]">
              Q
            </div>
            <h2 className="font-heading text-4xl font-bold text-[#3b2731]">Verify your email</h2>
            <p className="mt-2 text-sm text-[#7c6b67]">
              Enter the 6-digit PIN sent to <span className="font-bold text-[#633449]">{maskedEmail || "your email"}</span>.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="email-pin">
                Verification PIN
              </label>
              <input
                id="email-pin"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                className="auth-input text-center text-2xl font-black tracking-[0.45em]"
                placeholder="000000"
                value={pin}
                onChange={handlePinChange}
                maxLength={6}
                required
              />
            </div>

            <div className="rounded-2xl bg-[#fff4ed] p-3 text-sm leading-6 text-[#705f5b]">
              <b className="text-[#7b3d54]">Check your inbox:</b> the PIN expires in 5 minutes.
            </div>

            {notice && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-4 text-sm font-medium text-emerald-700">
                {notice}
              </div>
            )}

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !isPinValid}
              className="auth-submit w-full rounded-2xl bg-gradient-to-r from-[#b95777] to-[#7b3d54] px-5 py-4 font-bold text-white disabled:cursor-not-allowed disabled:opacity-70"
            >
              <span className="relative z-[1]">{loading ? "Verifying..." : "Verify and Continue"}</span>
            </button>

            <button
              type="button"
              onClick={handleResend}
              disabled={resending || resendCooldown > 0}
              className="w-full rounded-2xl border border-[#eadbd5] bg-white/70 px-5 py-3 font-bold text-[#7b3d54] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {resending
                ? "Sending..."
                : resendCooldown > 0
                  ? `Resend PIN in ${resendCooldown}s`
                  : "Resend verification PIN"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#71635f]">
            Used the wrong email?{" "}
            <Link to="/signup" className="font-bold text-[#9d3d5e] hover:underline">
              Go back to signup
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
};

export default VerifyEmail;
