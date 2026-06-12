import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { interestApi, trustSafetyApi } from "../services/api";

interface FullProfileResponse {
  id: string;
  name: string;
  email: string;
  age: number;
  gender: string;
  religion: string | null;
  nid: string;
  verification_status?: string | null;
  matching_percentage?: number | null;
  nid_verified?: boolean;
  photo_verified?: boolean;
  profile: {
    location?: string | null;
    profession?: string | null;
    academic_background?: string | null;
    marital_status?: string | null;
    hobbies?: string | null;
    interests?: string | null;
    overall_health_status?: string | null;
    blood_group?: string | null;
    dietary_preference?: string | null;
    smoking_habit?: string | null;
    alcohol_consumption?: string | null;
    preferred_age_min?: number | null;
    preferred_age_max?: number | null;
    preferred_religion?: string | null;
    preferred_location?: string | null;
    willing_to_relocate?: boolean | null;
    additional_comments?: string | null;
  };
}

const FullProfileView: React.FC = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<FullProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProfile = async () => {
      if (!userId) {
        setError("Invalid profile link.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await interestApi.getFullProfile(userId);
        setProfile(response as FullProfileResponse);
      } catch (err: any) {
        const message = err?.message || "Unable to load full profile.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void loadProfile();
  }, [userId]);

  const renderVerificationBadges = (data: FullProfileResponse) => {
    if (!data.nid_verified && !data.photo_verified) {
      return null;
    }

    return (
      <div className="flex flex-wrap gap-2 mt-2">
        {data.nid_verified && (
          <span
            className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5"
            title="NID verified by our team"
          >
            NID Verified
          </span>
        )}
        {data.photo_verified && (
          <span
            className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5"
            title="Photo verified via NID-to-photo match"
          >
            Photo Verified
          </span>
        )}
      </div>
    );
  };

  const handleReport = async () => {
    if (!profile) return;
    const reason = window.prompt('Why are you reporting this user? (e.g., harassment, scam, spam)');
    if (!reason || !reason.trim()) return;
    const details = window.prompt('Any additional details? (optional)');
    try {
      await trustSafetyApi.reportUser(profile.id, reason.trim(), details?.trim() || undefined, 'full_profile');
      alert('Report submitted. Thank you for helping keep the community safe.');
    } catch (err: any) {
      alert(err?.message || 'Failed to submit report');
    }
  };

  const handleBlock = async () => {
    if (!profile) return;
    if (!window.confirm(`Block ${profile.name}? You will no longer see each other.`)) return;
    try {
      await trustSafetyApi.blockUser(profile.id);
      alert(`${profile.name} has been blocked.`);
      navigate(-1);
    } catch (err: any) {
      alert(err?.message || 'Failed to block user');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Full Profile</h1>
              <p className="text-sm text-gray-500">Read-only view for matched users</p>
              {profile && renderVerificationBadges(profile)}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleReport}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm"
              >
                Report
              </button>
              <button
                onClick={handleBlock}
                className="px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md text-sm"
              >
                Block
              </button>
              <button
                onClick={() => navigate(-1)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md"
              >
                Back
              </button>
            </div>
          </div>

          {loading ? (
            <div className="py-16 text-center text-gray-500">Loading profile...</div>
          ) : error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">
              {error}
            </div>
          ) : profile ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div><span className="font-semibold text-gray-700">Name:</span> {profile.name}</div>
                <div><span className="font-semibold text-gray-700">Age:</span> {profile.age}</div>
                <div><span className="font-semibold text-gray-700">Gender:</span> {profile.gender}</div>
                <div><span className="font-semibold text-gray-700">Religion:</span> {profile.religion || "Not specified"}</div>
                <div><span className="font-semibold text-gray-700">Location:</span> {profile.profile.location || "Not specified"}</div>
                <div><span className="font-semibold text-gray-700">Profession:</span> {profile.profile.profession || "Not specified"}</div>
                <div><span className="font-semibold text-gray-700">Education:</span> {profile.profile.academic_background || "Not specified"}</div>
                <div><span className="font-semibold text-gray-700">Marital Status:</span> {profile.profile.marital_status || "Not specified"}</div>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-800 mb-3">Lifestyle & Health</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div><span className="font-semibold text-gray-700">Health:</span> {profile.profile.overall_health_status || "Not specified"}</div>
                  <div><span className="font-semibold text-gray-700">Blood Group:</span> {profile.profile.blood_group || "Not specified"}</div>
                  <div><span className="font-semibold text-gray-700">Diet:</span> {profile.profile.dietary_preference || "Not specified"}</div>
                  <div><span className="font-semibold text-gray-700">Smoking:</span> {profile.profile.smoking_habit || "Not specified"}</div>
                  <div><span className="font-semibold text-gray-700">Alcohol:</span> {profile.profile.alcohol_consumption || "Not specified"}</div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-800 mb-2">About</h3>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {profile.profile.hobbies || profile.profile.interests || profile.profile.additional_comments || "No additional details shared yet."}
                </p>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-800 mb-3">Partner Preferences</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="font-semibold text-gray-700">Preferred Age:</span>{" "}
                    {profile.profile.preferred_age_min ?? "Any"} - {profile.profile.preferred_age_max ?? "Any"}
                  </div>
                  <div><span className="font-semibold text-gray-700">Preferred Religion:</span> {profile.profile.preferred_religion || "Not specified"}</div>
                  <div><span className="font-semibold text-gray-700">Preferred Location:</span> {profile.profile.preferred_location || "Not specified"}</div>
                  <div>
                    <span className="font-semibold text-gray-700">Relocate:</span>{" "}
                    {profile.profile.willing_to_relocate == null ? "Not specified" : profile.profile.willing_to_relocate ? "Yes" : "No"}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default FullProfileView;
