import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../services/api";
import { Button, Input, Select, Card } from "../components/ui";

const SignUp: React.FC = () => {
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login, isLoggedIn, isAuthReady } = useAuth();

  useEffect(() => {
    if (isAuthReady && isLoggedIn) {
      navigate("/", { replace: true });
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

  return (
    isAuthReady && isLoggedIn ? (
      <Navigate to="/" replace />
    ) : (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-2xl">
        {/* Logo & Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-600 to-accent-600 rounded-2xl shadow-lg mb-4">
            <span className="text-white font-bold text-2xl">Q</span>
          </div>
          <h2 className="text-3xl font-heading font-bold bg-gradient-to-r from-primary-700 to-accent-700 bg-clip-text text-transparent">
            Create Your Account
          </h2>
          <p className="mt-2 text-gray-600">
            Start your journey to find your perfect match
          </p>
        </div>

        {/* Sign Up Card */}
        <Card className="animate-slide-up" padding="lg">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name */}
            <Input
              type="text"
              name="name"
              label="Full Name"
              placeholder="Enter your full name"
              value={formData.name}
              onChange={handleInputChange}
              required
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              }
            />

            {/* Email & Password Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Input
                type="email"
                name="email"
                label="Email Address"
                placeholder="your@email.com"
                value={formData.email}
                onChange={handleInputChange}
                required
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                  </svg>
                }
              />

              <Input
                type="password"
                name="password"
                label="Password"
                placeholder="Create a strong password"
                value={formData.password}
                onChange={handleInputChange}
                required
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                }
              />
            </div>

            {/* Gender & Age Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Select
                name="gender"
                label="Gender"
                value={formData.gender}
                onChange={handleInputChange}
                required
                options={[
                  { value: "", label: "Select Gender" },
                  { value: "Male", label: "Male" },
                  { value: "Female", label: "Female" },
                  { value: "Other", label: "Other" },
                ]}
              />

              <Input
                type="number"
                name="age"
                label="Age"
                placeholder="Your age"
                value={formData.age}
                min={18}
                max={99}
                onChange={handleInputChange}
                required
              />
            </div>

            {/* NID & Religion Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Input
                type="text"
                name="nid"
                label="National ID (NID)"
                placeholder="Enter your NID number"
                value={formData.nid}
                onChange={handleInputChange}
                required
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
                  </svg>
                }
              />

              <Input
                type="text"
                name="religion"
                label="Religion (Optional)"
                placeholder="Your religion"
                value={formData.religion}
                onChange={handleInputChange}
              />
            </div>

            {/* Preferred Age Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preferred Age Range
              </label>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  type="number"
                  name="from"
                  placeholder="From"
                  value={ageRange.from}
                  min={18}
                  max={99}
                  onChange={handleAgeRangeChange}
                />
                <Input
                  type="number"
                  name="to"
                  placeholder="To"
                  value={ageRange.to}
                  min={18}
                  max={99}
                  onChange={handleAgeRangeChange}
                />
              </div>
            </div>

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
              {loading ? "Creating Account..." : "Create Account"}
            </Button>
          </form>
        </Card>

        {/* Sign In Link */}
        <p className="text-center text-gray-600 mt-6 animate-fade-in">
          Already have an account?{" "}
          <Link to="/signin" className="text-primary-600 hover:text-primary-700 font-semibold">
            Sign In
          </Link>
        </p>
      </div>
    </div>
    )
  );
};

export default SignUp;
