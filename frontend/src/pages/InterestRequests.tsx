import React, { useState, useEffect } from "react";
import { interestApi } from "../services/api";
import { useNavigate } from "react-router-dom";

interface Interest {
  id: string;
  from_user_id: string;
  to_user_id: string;
  status: 'pending' | 'accepted' | 'rejected';
  message: string | null;
  created_at: string;
  updated_at: string | null;
  from_user?: {
    id: string;
    name: string;
    age: number;
    religion: string | null;
    profile_picture: string | null;
  };
  to_user?: {
    id: string;
    name: string;
    age: number;
    religion: string | null;
    profile_picture: string | null;
  };
}

interface FullProfileResponse {
  id: string;
  name: string;
  email: string;
  age: number;
  gender: string;
  religion: string | null;
  nid: string;
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

type InterestActionStatus = 'accepted' | 'rejected';

const HANDLED_INTEREST_NOTIFICATION_KEY = 'handledInterestNotifications';

const readHandledInterestNotificationMap = (): Record<string, InterestActionStatus> => {
  try {
    const raw = sessionStorage.getItem(HANDLED_INTEREST_NOTIFICATION_KEY);
    if (!raw) {
      return {};
    }
    return JSON.parse(raw) as Record<string, InterestActionStatus>;
  } catch {
    return {};
  }
};

const writeHandledInterestNotificationMap = (map: Record<string, InterestActionStatus>) => {
  try {
    sessionStorage.setItem(HANDLED_INTEREST_NOTIFICATION_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage errors.
  }
};

const rememberHandledInterest = (interestId: string, status: InterestActionStatus) => {
  const existingMap = readHandledInterestNotificationMap();
  writeHandledInterestNotificationMap({
    ...existingMap,
    [interestId]: status,
  });
};

const InterestRequests: React.FC = () => {
  const navigate = useNavigate();
  const [receivedInterests, setReceivedInterests] = useState<Interest[]>([]);
  const [sentInterests, setSentInterests] = useState<Interest[]>([]);
  const [activeTab, setActiveTab] = useState<'received' | 'sent'>('received');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [fullProfile, setFullProfile] = useState<FullProfileResponse | null>(null);

  useEffect(() => {
    loadInterests();
  }, []);

  const loadInterests = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [received, sent] = await Promise.all([
        interestApi.getReceivedInterests(),
        interestApi.getSentInterests()
      ]);
      
      setReceivedInterests(received.interests);
      setSentInterests(sent.interests);
    } catch (err: any) {
      setError(err.message || 'Failed to load interests');
      console.error('Error loading interests:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptInterest = async (interestId: string, userId: string, userName: string) => {
    if (!window.confirm(`Accept interest from ${userName}?`)) return;
    
    try {
      setProcessingId(interestId);
      await interestApi.acceptInterest(interestId);
      rememberHandledInterest(interestId, 'accepted');
      const profileResponse = await interestApi.getFullProfile(userId);
      setFullProfile(profileResponse as FullProfileResponse);
      await loadInterests();
      alert(`You and ${userName} are now matched! Full profile unlocked.`);
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to accept interest'}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleRejectInterest = async (interestId: string, userName: string) => {
    if (!window.confirm(`Reject interest from ${userName}?`)) return;
    
    try {
      setProcessingId(interestId);
      await interestApi.rejectInterest(interestId);
      rememberHandledInterest(interestId, 'rejected');
      await loadInterests();
      alert(`Interest from ${userName} rejected`);
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to reject interest'}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleCancelInterest = async (interestId: string, userName: string) => {
    if (!window.confirm(`Cancel your interest to ${userName}?`)) return;
    
    try {
      setProcessingId(interestId);
      await interestApi.cancelInterest(interestId);
      await loadInterests();
      alert(`Interest to ${userName} canceled`);
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to cancel interest'}`);
    } finally {
      setProcessingId(null);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays < 1) return "Today";
    if (diffDays < 2) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">Pending</span>;
      case 'accepted':
        return <span className="px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Accepted</span>;
      case 'rejected':
        return <span className="px-3 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">Rejected</span>;
      default:
        return null;
    }
  };

  const renderInterestCard = (interest: Interest, type: 'received' | 'sent') => {
    const user = type === 'received' ? interest.from_user : interest.to_user;
    if (!user) return null;

    return (
      <div key={interest.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
        <div className="flex items-center p-5">
          {/* User Avatar */}
          <div className="flex-shrink-0 mr-4">
            {user.profile_picture ? (
              <img
                src={user.profile_picture}
                alt={user.name}
                className="h-16 w-16 rounded-full object-cover"
                onError={(e) => {
                  e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&size=64&background=random`;
                }}
              />
            ) : (
              <div className="h-16 w-16 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center">
                <span className="text-white text-2xl font-bold">{user.name.charAt(0)}</span>
              </div>
            )}
          </div>

          {/* User Info */}
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900">{user.name}, {user.age}</h3>
            {user.religion && (
              <p className="text-sm text-gray-600">{user.religion}</p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {type === 'received' ? 'Sent' : 'Sent to them'}: {formatTimestamp(interest.created_at)}
            </p>
            {interest.message && (
              <p className="text-sm text-gray-700 mt-2 italic">"{interest.message}"</p>
            )}
          </div>

          {/* Status/Actions */}
          <div className="flex-shrink-0 ml-4">
            {interest.status === 'pending' && type === 'received' ? (
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => handleAcceptInterest(interest.id, user.id, user.name)}
                  disabled={processingId === interest.id}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-md disabled:opacity-50"
                >
                  {processingId === interest.id ? 'Processing...' : 'Accept'}
                </button>
                <button
                  onClick={() => handleRejectInterest(interest.id, user.name)}
                  disabled={processingId === interest.id}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            ) : interest.status === 'pending' && type === 'sent' ? (
              <button
                onClick={() => handleCancelInterest(interest.id, user.name)}
                disabled={processingId === interest.id}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md disabled:opacity-50"
              >
                {processingId === interest.id ? 'Canceling...' : 'Cancel'}
              </button>
            ) : interest.status === 'accepted' ? (
              <div className="flex flex-col gap-2 items-end">
                {getStatusBadge(interest.status)}
                <button
                  onClick={() => navigate(`/messages?user=${encodeURIComponent(user.id)}&name=${encodeURIComponent(user.name)}`)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-md"
                >
                  Message
                </button>
              </div>
            ) : (
              getStatusBadge(interest.status)
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Interest Requests</h1>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-6">
            <button
              onClick={() => setActiveTab('received')}
              className={`py-3 px-6 font-medium transition-colors ${
                activeTab === 'received'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Received ({receivedInterests.filter(i => i.status === 'pending').length})
            </button>
            <button
              onClick={() => setActiveTab('sent')}
              className={`py-3 px-6 font-medium transition-colors ${
                activeTab === 'sent'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Sent ({sentInterests.filter(i => i.status === 'pending').length})
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Full profile modal after mutual accept */}
          {fullProfile && (
            <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
              <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-2xl font-bold text-gray-800">{fullProfile.name}'s Full Profile</h2>
                  <p className="text-sm text-gray-500 mt-1">Unlocked after mutual interest</p>
                </div>

                <div className="p-6 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div><span className="font-semibold text-gray-700">Age:</span> {fullProfile.age}</div>
                    <div><span className="font-semibold text-gray-700">Gender:</span> {fullProfile.gender}</div>
                    <div><span className="font-semibold text-gray-700">Religion:</span> {fullProfile.religion || 'Not specified'}</div>
                    <div><span className="font-semibold text-gray-700">Location:</span> {fullProfile.profile.location || 'Not specified'}</div>
                    <div><span className="font-semibold text-gray-700">Profession:</span> {fullProfile.profile.profession || 'Not specified'}</div>
                    <div><span className="font-semibold text-gray-700">Education:</span> {fullProfile.profile.academic_background || 'Not specified'}</div>
                  </div>

                  <div className="rounded-lg border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-800 mb-3">Lifestyle & Health</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div><span className="font-semibold text-gray-700">Health:</span> {fullProfile.profile.overall_health_status || 'Not specified'}</div>
                      <div><span className="font-semibold text-gray-700">Blood Group:</span> {fullProfile.profile.blood_group || 'Not specified'}</div>
                      <div><span className="font-semibold text-gray-700">Diet:</span> {fullProfile.profile.dietary_preference || 'Not specified'}</div>
                      <div><span className="font-semibold text-gray-700">Smoking:</span> {fullProfile.profile.smoking_habit || 'Not specified'}</div>
                      <div><span className="font-semibold text-gray-700">Alcohol:</span> {fullProfile.profile.alcohol_consumption || 'Not specified'}</div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-800 mb-2">About</h3>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {fullProfile.profile.hobbies || fullProfile.profile.interests || fullProfile.profile.additional_comments || 'No additional details shared yet.'}
                    </p>
                  </div>

                  <div className="rounded-lg border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-800 mb-3">Partner Preferences</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="font-semibold text-gray-700">Preferred Age:</span>{' '}
                        {fullProfile.profile.preferred_age_min ?? 'Any'} - {fullProfile.profile.preferred_age_max ?? 'Any'}
                      </div>
                      <div><span className="font-semibold text-gray-700">Preferred Religion:</span> {fullProfile.profile.preferred_religion || 'Not specified'}</div>
                      <div><span className="font-semibold text-gray-700">Preferred Location:</span> {fullProfile.profile.preferred_location || 'Not specified'}</div>
                      <div>
                        <span className="font-semibold text-gray-700">Relocate:</span>{' '}
                        {fullProfile.profile.willing_to_relocate == null ? 'Not specified' : fullProfile.profile.willing_to_relocate ? 'Yes' : 'No'}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-6 border-t border-gray-200 flex flex-col sm:flex-row gap-3 sm:justify-end">
                  <button
                    onClick={() => {
                      navigate(`/messages?user=${encodeURIComponent(fullProfile.id)}`);
                      setFullProfile(null);
                    }}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
                  >
                    Start Chat
                  </button>
                  <button
                    onClick={() => setFullProfile(null)}
                    className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-md"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {activeTab === 'received' ? (
                receivedInterests.length > 0 ? (
                  receivedInterests.map(interest => renderInterestCard(interest, 'received'))
                ) : (
                  <div className="text-center py-16">
                    <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">No received interests</h3>
                    <p className="mt-2 text-sm text-gray-500">When someone sends you an interest, it will appear here.</p>
                  </div>
                )
              ) : (
                sentInterests.length > 0 ? (
                  sentInterests.map(interest => renderInterestCard(interest, 'sent'))
                ) : (
                  <div className="text-center py-16">
                    <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">No sent interests</h3>
                    <p className="mt-2 text-sm text-gray-500">Visit Find Matches to send interests to users you like.</p>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InterestRequests;
