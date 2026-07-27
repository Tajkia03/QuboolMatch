import React, { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, X } from "lucide-react";
import { Link } from "react-router-dom";

const SIGNUP_SUCCESS_NOTIFICATION_KEY = "signupSuccessNotification";

const SignupSuccessNotification: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(SIGNUP_SUCCESS_NOTIFICATION_KEY) !== "true") {
      return;
    }

    sessionStorage.removeItem(SIGNUP_SUCCESS_NOTIFICATION_KEY);
    setIsVisible(true);
  }, []);

  if (!isVisible) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed right-5 top-24 z-50 w-[min(92vw,30rem)] rounded-2xl border border-emerald-200 bg-white p-5 text-emerald-950 shadow-2xl shadow-emerald-950/15"
    >
      <div className="flex gap-4">
        <CheckCircle2 className="h-11 w-11 flex-none text-emerald-600" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <p className="text-xl font-bold leading-tight">Sign up successful</p>
            <button
              type="button"
              onClick={() => setIsVisible(false)}
              className="grid h-8 w-8 flex-none place-items-center rounded-full text-emerald-700 transition hover:bg-emerald-50"
              aria-label="Dismiss sign up success message"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
          <Link
            to="/nid-verification"
            onClick={() => setIsVisible(false)}
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-base font-bold text-white shadow-lg shadow-emerald-900/15 transition hover:bg-emerald-700"
          >
            Click here to continue with NID verification
            <ArrowRight className="h-5 w-5" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </div>
  );
};

export default SignupSuccessNotification;
