import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../services/api";

const SignUp: React.FC = () => {
  const ONBOARDING_PENDING_KEY = "verificationOnboardingPending";
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    gender: "",
    nid: "",
    age: "",
    religion: "",
  });
  const [ageRange, setAgeRange] = useState({ from: "", to: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login, isLoggedIn, isAuthReady } = useAuth();

  useEffect(() => {
    if (isAuthReady && isLoggedIn) {
      const onboardingPending = localStorage.getItem(ONBOARDING_PENDING_KEY) === "true";
      navigate(onboardingPending ? "/nid-verification" : "/", { replace: true });
    }
  }, [isAuthReady, isLoggedIn, navigate]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleAgeRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setAgeRange((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    // Client-side validations
    const ageNum = parseInt(formData.age || "0");
    if (isNaN(ageNum) || ageNum < 18) {
      setError("You must be at least 18 years old to sign up.");
      setLoading(false);
      return;
    }

    const fromNum = ageRange.from ? parseInt(ageRange.from) : null;
    const toNum = ageRange.to ? parseInt(ageRange.to) : null;

    if (fromNum !== null && fromNum < 18) {
      setError("Preferred age range 'From' must be at least 18.");
      setLoading(false);
      return;
    }
    if (toNum !== null && toNum < 18) {
      setError("Preferred age range 'To' must be at least 18.");
      setLoading(false);
      return;
    }

    // Ensure preferred range has lower value in 'from' and higher in 'to'
    if (fromNum !== null && toNum !== null && fromNum > toNum) {
      setError("Preferred age range 'From' must be less than or equal to 'To'.");
      setLoading(false);
      return;
    }
    const finalFrom = fromNum;
    const finalTo = toNum;
    try {
      // Prepare the complete signup data
      const signupData = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        gender: formData.gender,
        nid: formData.nid,
        age: ageNum,
        religion: formData.religion || null,
        preferred_age_from: finalFrom,
        preferred_age_to: finalTo,
      };

      // Call backend API for sign up
      const response = await fetch(`${API_BASE_URL}/auth/sign_up`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(signupData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to sign up");
      }
      
      // Get the access token from the response
      const data = await response.json();
      
      // Log the user in with the real token
      localStorage.setItem(ONBOARDING_PENDING_KEY, "true");
      login(data.access_token);
      
      // Navigate directly to NID verification page
      navigate("/nid-verification", { replace: true });
    } catch (err) {
      console.error("Signup error:", err);
      setError(err instanceof Error ? err.message : "An error occurred during signup");
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
      <div className="auth-symbol auth-symbol-five">♡</div>

      <Link to="/#home" className="absolute left-5 top-5 z-10 flex items-center gap-3 font-bold text-[#633449] sm:left-10 sm:top-7">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#b95777] to-[#71384e] text-white shadow-[0_13px_30px_rgba(128,54,78,0.19)]">Q</span>
        <span>Qubool Match</span>
      </Link>
      <Link to="/#home" className="absolute right-5 top-8 z-10 hidden text-sm font-semibold text-[#7c5a62] hover:text-[#b95777] sm:block">
        ← Back to home
      </Link>

      <div className="auth-enter relative z-[2] grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.75fr_1.25fr]">
        <aside className="hidden px-4 text-[#563442] lg:block">
          <span className="inline-flex rounded-full border border-white/70 bg-white/55 px-4 py-2 text-xs font-extrabold uppercase tracking-[0.18em] text-[#8c3d5b] shadow-[0_12px_30px_rgba(112,53,75,0.07)]">
            Private • Verified • Meaningful
          </span>
          <h1 className="mt-5 font-heading text-6xl font-bold leading-[0.96] tracking-[-0.04em] text-[#3c2731]">
            Begin with trust, continue with <span className="text-[#b95777]">intention.</span>
          </h1>
          <p className="mt-5 max-w-md leading-7 text-[#705f5b]">
            Create your profile with the essentials first. After that, we guide you into verification.
          </p>
        </aside>

        <section className="auth-card-glass relative w-full rounded-[2rem] p-6 sm:p-8">
          <div className="mb-6 text-center">
            <div className="auth-bob mx-auto mb-4 grid h-16 w-16 place-items-center rounded-[1.35rem] bg-gradient-to-br from-[#b95777] to-[#7b3d54] text-2xl font-black text-white shadow-[0_16px_34px_rgba(135,52,78,0.19)]">
              Q
            </div>
            <h2 className="font-heading text-4xl font-bold text-[#3b2731]">Create your account</h2>
            <p className="mt-2 text-sm text-[#7c6b67]">Start your journey to find a thoughtful match.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-name">Full name</label>
              <input
                id="signup-name"
                type="text"
                name="name"
                className="auth-input"
                placeholder="Enter your full name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-email">Email address</label>
                <input
                  id="signup-email"
                  type="email"
                  name="email"
                  className="auth-input"
                  placeholder="your@email.com"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-password">Password</label>
                <div className="relative">
                  <input
                    id="signup-password"
                    type={showPassword ? "text" : "password"}
                    name="password"
                    className="auth-input pr-16"
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                  />
                  <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-[#8b7178] hover:text-[#b95777]">
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-gender">Gender</label>
                <select id="signup-gender" name="gender" className="auth-input" value={formData.gender} onChange={handleInputChange} required>
                  <option value="">Select Gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-age">Age</label>
                <input
                  id="signup-age"
                  type="number"
                  name="age"
                  className="auth-input"
                  placeholder="Your age"
                  value={formData.age}
                  min={18}
                  max={99}
                  onChange={handleInputChange}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-nid">National ID (NID)</label>
                <input
                  id="signup-nid"
                  type="text"
                  name="nid"
                  className="auth-input"
                  placeholder="Enter your NID number"
                  value={formData.nid}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]" htmlFor="signup-religion">Religion <span className="normal-case text-[#9b8b86]">(Optional)</span></label>
                <input
                  id="signup-religion"
                  type="text"
                  name="religion"
                  className="auth-input"
                  placeholder="Your religion"
                  value={formData.religion}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-[#5f514d]">Preferred age range</label>
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="number"
                  name="from"
                  className="auth-input"
                  placeholder="From"
                  value={ageRange.from}
                  min={18}
                  max={99}
                  onChange={handleAgeRangeChange}
                />
                <input
                  type="number"
                  name="to"
                  className="auth-input"
                  placeholder="To"
                  value={ageRange.to}
                  min={18}
                  max={99}
                  onChange={handleAgeRangeChange}
                />
              </div>
            </div>

            <div className="rounded-2xl bg-[#fff4ed] p-3 text-sm leading-6 text-[#705f5b]">
              <b className="text-[#7b3d54]">Next step:</b> after account creation, we will guide you to NID verification.
            </div>

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="auth-submit w-full rounded-2xl bg-gradient-to-r from-[#b95777] to-[#7b3d54] px-5 py-4 font-bold text-white disabled:cursor-not-allowed disabled:opacity-70">
              <span className="relative z-[1]">{loading ? "Creating Account..." : "Create Account"}</span>
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#71635f]">
            Already have an account?{" "}
            <Link to="/signin" className="font-bold text-[#9d3d5e] hover:underline">
              Sign In
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
};

export default SignUp;
