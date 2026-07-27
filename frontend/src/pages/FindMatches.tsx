import React, { useState, useEffect } from "react";
import { interestApi, trustSafetyApi } from "../services/api";
import { useNavigate } from "react-router-dom";

type MatchExplanationRow = {
  key: string;
  label: string;
  matched: boolean | null;
  required: boolean;
  user_preference: string;
  candidate_value: string;
  candidate_preference?: string;
  note?: string;
};

type MatchExplanation = {
  overall_score: number;
  similarity_score: number;
  preference_score: number;
  strict_compatible: boolean;
  reason_tags: string[];
  relaxed_preferences?: string[];
  rows: MatchExplanationRow[];
};

// Define the structure for a user from the API
interface User {
  id: string;
  name: string;
  age: number;
  gender: string;
  religion: string | null;
  location: string | null;
  profession: string | null;
  academic_background: string | null;
  profile_picture: string | null;
  interest_status: 'none' | 'pending_sent' | 'pending_received' | 'accepted' | 'rejected';
  verification_status?: string | null;
  matching_percentage?: number | null;
  nid_verified?: boolean;
  photo_verified?: boolean;
  // Overview fields
  marital_status?: string | null;
  height?: number | null;
  weight?: number | null;
  interests?: string | null;
  hobbies?: string | null;
  dietary_preference?: string | null;
  smoking_habit?: string | null;
  alcohol_consumption?: string | null;
  overall_health_status?: string | null;
  blood_group?: string | null;
  preferred_age_min?: number | null;
  preferred_age_max?: number | null;
  living_with_in_laws?: string | null;
  willing_to_relocate?: boolean | null;
  recommendation_reasons?: string[];
  match_explanation?: MatchExplanation | null;
}

type ViewMode = 'all' | 'recommended' | 'interested';
type OverviewTab = 'overview' | 'matched';

interface MatchResponse {
  id: string;
  matched_user: {
    id: string;
    name: string;
    age: number;
    religion: string | null;
    profile_picture: string | null;
    verification_status?: string | null;
    matching_percentage?: number | null;
    nid_verified?: boolean;
    photo_verified?: boolean;
  };
}

const FindMatches: React.FC = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sendingInterest, setSendingInterest] = useState<string | null>(null);
  const [cancelingInterest, setCancelingInterest] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [mlReady, setMlReady] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [overviewTab, setOverviewTab] = useState<OverviewTab>('overview');
  
  const [filters, setFilters] = useState({
    location: '',
    religion: 'all',
    gender: 'all',
    minAge: 18,
    maxAge: 60
  });

  // Load users on component mount
  useEffect(() => {
    setPage(1);
    loadUsers(viewMode, 1);
  }, []);

  // Reload when view mode changes
  useEffect(() => {
    setPage(1);
    setUsers([]);
    setFilteredUsers([]);
    loadUsers(viewMode, 1);
  }, [viewMode]);

  const loadUsers = async (mode: ViewMode = 'all', pageNum: number = 1, append: boolean = false) => {
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);
      let response;
      if (mode === 'recommended') {
        response = await interestApi.getRecommendations(pageNum, 20);
        const ready = response.ml_ready ?? false;
        setMlReady(ready);
        if (!ready) {
          setError('AI recommendation model is not trained yet. Please run "python retrain_model.py" in the backend to enable this feature.');
          setUsers([]);
          setFilteredUsers([]);
          setHasMore(false);
          return;
        }
      } else if (mode === 'interested') {
        response = await interestApi.getMatches();
        setMlReady(false);
      } else {
        response = await interestApi.browseUsers(pageNum, 20);
        setMlReady(false);
      }

      if (mode === 'interested') {
        const matches = (response.matches || []) as MatchResponse[];
        const newUsers = matches.map((match) => ({
          id: match.matched_user.id,
          name: match.matched_user.name,
          age: match.matched_user.age,
          gender: '',
          religion: match.matched_user.religion,
          location: null,
          profession: null,
          academic_background: null,
          profile_picture: match.matched_user.profile_picture,
          interest_status: 'accepted' as const,
          verification_status: match.matched_user.verification_status,
          matching_percentage: match.matched_user.matching_percentage,
          nid_verified: match.matched_user.nid_verified,
          photo_verified: match.matched_user.photo_verified,
        }));
        setUsers(newUsers);
        setFilteredUsers(newUsers);
        setHasMore(false);
        return;
      }

      const newUsers = response.users;
      const pagination = response.pagination;

      if (append) {
        setUsers(prev => [...prev, ...newUsers]);
        setFilteredUsers(prev => [...prev, ...newUsers]);
      } else {
        setUsers(newUsers);
        setFilteredUsers(newUsers);
      }

      setHasMore(pagination?.has_more ?? false);
    } catch (err: any) {
      setError(err.message || 'Failed to load users');
      console.error('Error loading users:', err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMoreUsers = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadUsers(viewMode, nextPage, true);
  };

  // Apply filters when filter state changes
  useEffect(() => {
    const filtered = users.filter(user => {
      if (filters.location && !user.location?.toLowerCase().includes(filters.location.toLowerCase())) {
        return false;
      }
      if (filters.religion !== 'all' && user.religion !== filters.religion) {
        return false;
      }
      if (filters.gender !== 'all' && user.gender !== filters.gender) {
        return false;
      }
      if (user.age < filters.minAge || user.age > filters.maxAge) {
        return false;
      }
      return true;
    });
    setFilteredUsers(filtered);
  }, [filters, users]);

  const handleFilterChange = (name: string, value: any) => {
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleSendInterest = async (userId: string, userName: string) => {
    if (!window.confirm(`Send interest to ${userName}?`)) return;
    try {
      setSendingInterest(userId);
      await interestApi.sendInterest(userId, `Hi ${userName}, I'd like to connect with you!`);
      setPage(1);
      await loadUsers(viewMode, 1);
      alert(`Interest sent to ${userName} successfully!`);
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to send interest'}`);
    } finally {
      setSendingInterest(null);
    }
  };

  const handleCancelInterest = async (userId: string, userName: string) => {
    if (!window.confirm(`Cancel your interest to ${userName}?`)) return;
    try {
      setCancelingInterest(userId);
      // We need to get the interest ID first
      const sentInterests = await interestApi.getSentInterests();
      const interest = sentInterests.interests.find((i: any) => i.to_user_id === userId && i.status === 'pending');
      if (interest) {
        await interestApi.cancelInterest(interest.id);
        setPage(1);
        await loadUsers(viewMode, 1);
        alert(`Interest to ${userName} canceled successfully!`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to cancel interest'}`);
    } finally {
      setCancelingInterest(null);
    }
  };

  const getInterestButtonText = (status: string) => {
    switch (status) {
      case 'pending_sent': return 'Interest Sent';
      case 'pending_received': return 'Respond to Interest';
      case 'accepted': return 'Matched ✓';
      case 'rejected': return 'Declined';
      default: return 'Send Interest';
    }
  };

  const getInterestButtonClass = (status: string) => {
    switch (status) {
      case 'pending_sent': return 'bg-yellow-500 hover:bg-yellow-600 cursor-not-allowed';
      case 'pending_received': return 'bg-green-600 hover:bg-green-700';
      case 'accepted': return 'bg-blue-600 hover:bg-blue-700 cursor-default';
      case 'rejected': return 'bg-gray-400 cursor-not-allowed';
      default: return 'bg-pink-600 hover:bg-pink-700';
    }
  };

  const isButtonDisabled = (status: string, userId: string) => {
    return status === 'pending_sent' || status === 'accepted' || status === 'rejected' || sendingInterest === userId;
  };

  const openOverviewModal = (user: User, tab: OverviewTab = 'overview') => {
    setSelectedUser(user);
    setOverviewTab(tab);
  };

  const shouldShowMatchExplanation = (user: User | null) => {
    return viewMode === 'recommended' && mlReady && Boolean(user?.match_explanation);
  };

  const formatPercent = (value?: number | null) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return '0%';
    }
    return `${Math.round(value * 100)}%`;
  };

  const getMatchRowClasses = (matched: boolean | null) => {
    if (matched === true) {
      return 'border-emerald-200 bg-emerald-50 text-emerald-900';
    }
    if (matched === false) {
      return 'border-amber-200 bg-amber-50 text-amber-950';
    }
    return 'border-gray-200 bg-gray-50 text-gray-800';
  };

  const getMatchRowBadge = (matched: boolean | null) => {
    if (matched === true) {
      return 'Matched';
    }
    if (matched === false) {
      return 'Relaxed';
    }
    return 'Neutral';
  };

  const renderVerificationBadges = (user: User) => {
    if (!user.nid_verified && !user.photo_verified) {
      return null;
    }

    return (
      <div className="flex flex-wrap gap-2 mt-2">
        {user.nid_verified && (
          <span
            className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5"
            title="NID verified by our team"
          >
            NID Verified
          </span>
        )}
        {user.photo_verified && (
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

  const handleReportUser = async (user: User) => {
    const reason = window.prompt('Why are you reporting this user? (e.g., harassment, scam, spam)');
    if (!reason || !reason.trim()) {
      return;
    }

    const details = window.prompt('Any additional details? (optional)');
    try {
      await trustSafetyApi.reportUser(user.id, reason.trim(), details?.trim() || undefined, 'matches');
      alert('Report submitted. Thank you for helping keep the community safe.');
    } catch (err: any) {
      alert(err?.message || 'Failed to submit report');
    }
  };

  const handleBlockUser = async (user: User) => {
    if (!window.confirm(`Block ${user.name}? You will no longer see each other.`)) {
      return;
    }

    try {
      await trustSafetyApi.blockUser(user.id);
      setUsers((prev) => prev.filter((item) => item.id !== user.id));
      setFilteredUsers((prev) => prev.filter((item) => item.id !== user.id));
      if (selectedUser?.id === user.id) {
        setSelectedUser(null);
      }
      alert(`${user.name} has been blocked.`);
    } catch (err: any) {
      alert(err?.message || 'Failed to block user');
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f5f8] pb-12">
      <div className="overflow-hidden bg-gradient-to-br from-[#30204f] via-[#694390] to-[#b7547c] text-white shadow-xl">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-pink-200">Thoughtful connections</p>
          <h1 className="mt-3 text-4xl font-extrabold tracking-tight sm:text-5xl">Find someone worth knowing.</h1>
          <p className="mt-3 max-w-2xl text-sm text-purple-100 sm:text-base">Thoughtful recommendations shaped by what matters to you—not an endless swipe.</p>

          {/* View Mode Toggle */}
          <div className="mt-8 flex">
            <div className="inline-flex flex-wrap gap-2">
              <button
                onClick={() => setViewMode('all')}
                className={`rounded-full border px-5 py-2 text-sm font-medium transition-all ${
                  viewMode === 'all'
                    ? 'border-white bg-white text-[#513172] shadow-lg'
                    : 'border-white/25 bg-white/5 text-purple-100 hover:bg-white/10'
                }`}
              >
                All Profiles
              </button>
              <button
                onClick={() => setViewMode('recommended')}
                className={`rounded-full border px-5 py-2 text-sm font-medium transition-all ${
                  viewMode === 'recommended'
                    ? 'border-white bg-white text-[#513172] shadow-lg'
                    : 'border-white/25 bg-white/5 text-purple-100 hover:bg-white/10'
                }`}
              >
                ✨ Recommended
              </button>
              <button
                onClick={() => setViewMode('interested')}
                className={`rounded-full border px-5 py-2 text-sm font-medium transition-all ${
                  viewMode === 'interested'
                    ? 'border-white bg-white text-[#513172] shadow-lg'
                    : 'border-white/25 bg-white/5 text-purple-100 hover:bg-white/10'
                }`}
              >
                Interested
              </button>
            </div>
          </div>

          {/* AI badge — only shown when model is ready in recommended mode */}
          {viewMode === 'recommended' && mlReady && (
            <div className="mt-4 flex items-center">
              <span className="inline-flex items-center gap-1 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM6.343 5.343a1 1 0 00-1.414 1.414l.707.707A1 1 0 007.05 6.05l-.707-.707zM3 10a1 1 0 100 2h1a1 1 0 100-2H3zM14.657 5.343a1 1 0 010 1.414l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 10a1 1 0 100 2h-1a1 1 0 100-2h1zM10 17a1 1 0 100-2h-.01a1 1 0 100 2H10zM7.05 13.95a1 1 0 010 1.414l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 0zM13.657 13.95a1 1 0 00-1.414 0l-.707.707a1 1 0 001.414 1.414l.707-.707a1 1 0 000-1.414z"/></svg>
                Ranked by AI · Based on your profile compatibility
              </span>
            </div>
          )}
          <div className="mt-6 rounded-xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-pink-200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-purple-50">
                  You can send interest to users. Maximum 3 mutual interests allowed. Full profiles are visible only after mutual interest.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="relative -mt-1 pt-7">
          
          {/* Filters Section */}
          {viewMode !== 'interested' && (
            <div className="mb-8 rounded-2xl border border-purple-100 bg-white p-5 shadow-[0_14px_40px_rgba(65,37,81,0.10)]">
              <h2 className="mb-4 text-lg font-semibold text-gray-800">Refine your matches</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                  <input 
                    type="text" 
                    placeholder="City, Country"
                    className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 shadow-sm outline-none transition focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                    value={filters.location}
                    onChange={(e) => handleFilterChange('location', e.target.value)}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Religion</label>
                  <select 
                    className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 shadow-sm outline-none transition focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                    value={filters.religion}
                    onChange={(e) => handleFilterChange('religion', e.target.value)}
                  >
                    <option value="all">All</option>
                    <option value="Islam">Islam</option>
                    <option value="Hinduism">Hinduism</option>
                    <option value="Christianity">Christianity</option>
                    <option value="Buddhism">Buddhism</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                  <select 
                    className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 shadow-sm outline-none transition focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                    value={filters.gender}
                    onChange={(e) => handleFilterChange('gender', e.target.value)}
                  >
                    <option value="all">All</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Age: {filters.minAge} - {filters.maxAge}
                  </label>
                  <div className="flex gap-2">
                    <input 
                      type="number" 
                      min="18" 
                      max="100"
                      placeholder="Min"
                      className="w-1/2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 shadow-sm outline-none transition focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                      value={filters.minAge}
                      onChange={(e) => handleFilterChange('minAge', parseInt(e.target.value) || 18)}
                    />
                    <input 
                      type="number" 
                      min="18" 
                      max="100"
                      placeholder="Max"
                      className="w-1/2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 shadow-sm outline-none transition focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                      value={filters.maxAge}
                      onChange={(e) => handleFilterChange('maxAge', parseInt(e.target.value) || 60)}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
          
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
          
          {/* Results Section */}
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            </div>
          ) : error ? null : viewMode === 'interested' ? (
            filteredUsers.length > 0 ? (
              <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">Mutual Connections</h2>
                <div className="space-y-3">
                  {filteredUsers.map((user) => (
                    <div key={user.id} className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
                      <div className="flex items-center gap-3">
                        {user.profile_picture ? (
                          <img src={user.profile_picture} alt={user.name} className="h-12 w-12 rounded-full object-cover" />
                        ) : (
                          <div className="h-12 w-12 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-semibold">
                            {user.name.charAt(0)}
                          </div>
                        )}
                        <div>
                          <button
                            onClick={() => navigate(`/profiles/${encodeURIComponent(user.id)}/full`)}
                            className="text-left text-sm font-semibold text-indigo-700 hover:text-indigo-900"
                          >
                            {user.name}
                          </button>
                          <div className="text-xs text-gray-500">{user.religion || 'Matched user'}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => navigate(`/messages?user=${encodeURIComponent(user.id)}&name=${encodeURIComponent(user.name)}`)}
                        className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-md"
                      >
                        Message
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-16">
                <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-3.314 0-6 2.239-6 5s2.686 5 6 5 6-2.239 6-5-2.686-5-6-5zm0 0V6a2 2 0 10-4 0v2m4 0a2 2 0 114 0v2" />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No mutual connections yet</h3>
                <p className="mt-2 text-sm text-gray-500">Accept interests to build your list here.</p>
              </div>
            )
          ) : filteredUsers.length > 0 ? (
            <>
              <div className="mb-5 flex items-center justify-between">
                <p className="font-semibold text-gray-800">{filteredUsers.length} profile{filteredUsers.length !== 1 ? 's' : ''} match your preferences</p>
                <span className="text-sm text-gray-500">Best match first</span>
              </div>
              <div className="grid grid-cols-1 items-start gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {filteredUsers.map((user) => (
                  <div key={user.id} className="overflow-hidden rounded-2xl border border-purple-100 bg-white shadow-[0_8px_28px_rgba(57,38,79,0.06)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_16px_38px_rgba(57,38,79,0.14)]">
                    {/* Profile Image */}
                    <div className="relative">
                      {user.profile_picture ? (
                        <img 
                          src={user.profile_picture} 
                          alt={`${user.name}'s profile`}
                          className="h-48 w-full object-cover object-center"
                          onError={(e) => {
                            e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&size=400&background=random`;
                          }}
                        />
                      ) : (
                        <div className="flex h-48 w-full items-center justify-center bg-gradient-to-br from-indigo-400 via-purple-500 to-fuchsia-500">
                          <span className="text-5xl font-bold text-white">{user.name.charAt(0)}</span>
                        </div>
                      )}
                      
                      {/* Interest Status Badge */}
                      {user.interest_status !== 'none' && (
                        <div className="absolute top-3 right-3">
                          {user.interest_status === 'accepted' && (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500 text-white">
                              ✓ Matched
                            </span>
                          )}
                          {user.interest_status === 'pending_sent' && (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-500 text-white">
                              ⏳ Pending
                            </span>
                          )}
                          {user.interest_status === 'pending_received' && (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-500 text-white">
                              💌 Interested in You
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    
                    {/* Profile Details */}
                    <div className="p-4 sm:p-5">
                      <h3 className="text-lg font-bold tracking-tight text-gray-800">{user.name}, {user.age}</h3>
                      {renderVerificationBadges(user)}
                      {shouldShowMatchExplanation(user) && (
                        <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                          <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                            <path fillRule="evenodd" d="M16.704 5.29a1 1 0 010 1.42l-7.25 7.2a1 1 0 01-1.41-.01l-3.25-3.34a1 1 0 111.43-1.4l2.55 2.62 6.54-6.5a1 1 0 011.39.01z" clipRule="evenodd" />
                          </svg>
                          AI matched preferences
                        </div>
                      )}
                      {viewMode === 'recommended' && user.recommendation_reasons && user.recommendation_reasons.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {user.recommendation_reasons.map((reason) => (
                            <span key={reason} className="rounded-full bg-pink-50 px-2 py-1 text-xs font-medium text-pink-700">
                              {reason}
                            </span>
                          ))}
                        </div>
                      )}
                      
                      <div className="mt-2 text-sm text-gray-600 space-y-1">
                        {user.location && (
                          <div className="flex items-center">
                            <svg className="h-4 w-4 text-gray-400 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                            </svg>
                            {user.location}
                          </div>
                        )}
                        
                        {user.profession && (
                          <div className="flex items-center">
                            <svg className="h-4 w-4 text-gray-400 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M6 6V5a3 3 0 013-3h2a3 3 0 013 3v1h2a2 2 0 012 2v3.57A22.952 22.952 0 0110 13a22.95 22.95 0 01-8-1.43V8a2 2 0 012-2h2zm2-1a1 1 0 011-1h2a1 1 0 011 1v1H8V5zm1 5a1 1 0 011-1h.01a1 1 0 110 2H10a1 1 0 01-1-1z" clipRule="evenodd" />
                            </svg>
                            {user.profession}
                          </div>
                        )}
                        
                        {user.religion && (
                          <div className="flex items-center">
                            <svg className="h-4 w-4 text-gray-400 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
                            </svg>
                            {user.religion}
                          </div>
                        )}
                        
                        {user.academic_background && (
                          <div className="flex items-center">
                            <svg className="h-4 w-4 text-gray-400 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838L7.667 9.088l1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3zM3.31 9.397L5 10.12v4.102a8.969 8.969 0 00-1.05-.174 1 1 0 01-.89-.89 11.115 11.115 0 01.25-3.762zM9.3 16.573A9.026 9.026 0 007 14.935v-3.957l1.818.78a3 3 0 002.364 0l5.508-2.361a11.026 11.026 0 01.25 3.762 1 1 0 01-.89.89 8.968 8.968 0 00-5.35 2.524 1 1 0 01-1.4 0zM6 18a1 1 0 001-1v-2.065a8.935 8.935 0 00-2-.712V17a1 1 0 001 1z" />
                            </svg>
                            {user.academic_background}
                          </div>
                        )}
                      </div>
                      
                      {/* Action Buttons */}
                      <div className="mt-4 space-y-2">
                        {/* View Overview Button */}
                        <button
                          onClick={() => openOverviewModal(user)}
                          className="flex w-full items-center justify-center gap-2 rounded-xl bg-purple-50 px-4 py-2.5 font-medium text-purple-700 transition-colors hover:bg-purple-100"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          View Overview
                        </button>
                        {shouldShowMatchExplanation(user) && (
                          <button
                            onClick={() => openOverviewModal(user, 'matched')}
                            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-50 px-4 py-2.5 font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7 4h10a2 2 0 012 2v12a2 2 0 01-2 2H7a2 2 0 01-2-2V6a2 2 0 012-2z" />
                            </svg>
                            Why Matched
                          </button>
                        )}
                        
                        {/* Interest Action Buttons */}
                        {user.interest_status === 'pending_sent' ? (
                          <div className="space-y-2">
                            <button 
                              disabled
                              className="w-full bg-yellow-500 text-white py-2 px-4 rounded-md font-medium cursor-not-allowed opacity-70"
                            >
                              Interest Sent
                            </button>
                            <button 
                              onClick={() => handleCancelInterest(user.id, user.name)}
                              disabled={cancelingInterest === user.id}
                              className="w-full bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded-md font-medium transition-colors disabled:opacity-50"
                            >
                              {cancelingInterest === user.id ? 'Canceling...' : 'Cancel Interest'}
                            </button>
                          </div>
                        ) : user.interest_status === 'accepted' ? (
                          <div className="space-y-2">
                            <button
                              onClick={() => navigate(`/profiles/${encodeURIComponent(user.id)}/full`)}
                              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 px-4 rounded-md font-medium transition-colors"
                            >
                              View Full Profile
                            </button>
                            <button
                              onClick={() => navigate(`/messages?user=${encodeURIComponent(user.id)}&name=${encodeURIComponent(user.name)}`)}
                              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 px-4 rounded-md font-medium transition-colors"
                            >
                              Message
                            </button>
                          </div>
                        ) : user.interest_status === 'pending_received' ? (
                          <button
                            onClick={() => navigate('/interest-requests')}
                            className="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-md font-medium transition-colors"
                          >
                            Respond to Interest
                          </button>
                        ) : (
                          <button 
                            onClick={() => user.interest_status === 'none' && handleSendInterest(user.id, user.name)}
                            disabled={isButtonDisabled(user.interest_status, user.id)}
                            className={`w-full ${getInterestButtonClass(user.interest_status)} text-white py-2 px-4 rounded-md font-medium transition-colors disabled:opacity-70`}
                          >
                            {sendingInterest === user.id ? 'Sending...' : getInterestButtonText(user.interest_status)}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Load More Button */}
              {hasMore && !loading && (
                <div className="mt-8 text-center">
                  <button
                    onClick={loadMoreUsers}
                    disabled={loadingMore}
                    className="inline-flex items-center px-6 py-3 bg-pink-600 hover:bg-pink-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loadingMore ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Loading...
                      </>
                    ) : (
                      'Load More Profiles'
                    )}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16">
              <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900">No users found</h3>
              <p className="mt-2 text-sm text-gray-500">Try adjusting your filters or check back later.</p>
            </div>
          )}
        </div>
      </div>

      {/* Profile Overview Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedUser(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="sticky top-0 bg-gradient-to-r from-pink-500 to-purple-600 text-white p-6 rounded-t-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {selectedUser.profile_picture ? (
                    <img 
                      src={selectedUser.profile_picture} 
                      alt={selectedUser.name}
                      className="w-16 h-16 rounded-full object-cover border-4 border-white shadow-lg"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded-full bg-white bg-opacity-20 flex items-center justify-center border-4 border-white shadow-lg">
                      <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                    </div>
                  )}
                  <div>
                    <h2 className="text-2xl font-bold">{selectedUser.name}, {selectedUser.age}</h2>
                    <p className="text-pink-100">{selectedUser.gender}</p>
                    {renderVerificationBadges(selectedUser)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReportUser(selectedUser)}
                    className="px-3 py-1.5 text-xs font-medium bg-white/20 hover:bg-white/30 rounded-full"
                  >
                    Report
                  </button>
                  <button
                    onClick={() => handleBlockUser(selectedUser)}
                    className="px-3 py-1.5 text-xs font-medium bg-white/20 hover:bg-white/30 rounded-full"
                  >
                    Block
                  </button>
                  <button 
                    onClick={() => setSelectedUser(null)}
                    className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {shouldShowMatchExplanation(selectedUser) && (
                <div className="flex rounded-xl bg-gray-100 p-1">
                  <button
                    type="button"
                    onClick={() => setOverviewTab('overview')}
                    className={`flex-1 rounded-lg px-4 py-2 text-sm font-bold transition ${
                      overviewTab === 'overview'
                        ? 'bg-white text-purple-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverviewTab('matched')}
                    className={`flex-1 rounded-lg px-4 py-2 text-sm font-bold transition ${
                      overviewTab === 'matched'
                        ? 'bg-white text-emerald-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Matched Preferences
                  </button>
                </div>
              )}

              {overviewTab === 'matched' && selectedUser.match_explanation ? (
                <section className="space-y-5">
                  <div className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-white p-5">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">Why the model matched you</h3>
                        <p className="mt-1 text-sm text-gray-600">
                          These rows come from the recommendation model's mutual preference checks.
                        </p>
                      </div>
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${
                        selectedUser.match_explanation.strict_compatible
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {selectedUser.match_explanation.strict_compatible ? 'Strict match' : 'Relaxed match'}
                      </span>
                    </div>

                    <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div className="rounded-xl bg-white p-4 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Overall</p>
                        <p className="mt-1 text-2xl font-black text-emerald-700">{formatPercent(selectedUser.match_explanation.overall_score)}</p>
                      </div>
                      <div className="rounded-xl bg-white p-4 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Similarity</p>
                        <p className="mt-1 text-2xl font-black text-purple-700">{formatPercent(selectedUser.match_explanation.similarity_score)}</p>
                      </div>
                      <div className="rounded-xl bg-white p-4 shadow-sm">
                        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Preference</p>
                        <p className="mt-1 text-2xl font-black text-pink-700">{formatPercent(selectedUser.match_explanation.preference_score)}</p>
                      </div>
                    </div>

                    {selectedUser.match_explanation.reason_tags.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {selectedUser.match_explanation.reason_tags.map((reason) => (
                          <span key={reason} className="rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-700 shadow-sm">
                            {reason}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    {selectedUser.match_explanation.rows.map((row) => (
                      <div key={row.key} className={`rounded-2xl border p-4 ${getMatchRowClasses(row.matched)}`}>
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="font-bold">{row.label}</h4>
                              <span className="rounded-full bg-white/75 px-2 py-0.5 text-[11px] font-bold">
                                {getMatchRowBadge(row.matched)}
                              </span>
                              {row.required && (
                                <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[11px] font-bold text-purple-700">
                                  Required
                                </span>
                              )}
                            </div>
                            {row.note && <p className="mt-1 text-sm opacity-80">{row.note}</p>}
                          </div>
                        </div>
                        <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
                          <div className="rounded-xl bg-white/70 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide opacity-60">Your Preference</p>
                            <p className="mt-1 font-semibold capitalize">{row.user_preference}</p>
                          </div>
                          <div className="rounded-xl bg-white/70 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide opacity-60">Their Profile</p>
                            <p className="mt-1 font-semibold capitalize">{row.candidate_value}</p>
                          </div>
                          <div className="rounded-xl bg-white/70 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide opacity-60">Their Preference</p>
                            <p className="mt-1 font-semibold capitalize">{row.candidate_preference || 'Not specified'}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ) : (
              <>
              {/* Basic Information */}
              <section>
                <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" />
                  </svg>
                  Basic Information
                </h3>
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  {selectedUser.religion && (
                    <div>
                      <p className="text-sm text-gray-600">Religion</p>
                      <p className="font-medium text-gray-900">{selectedUser.religion}</p>
                    </div>
                  )}
                  {selectedUser.location && (
                    <div>
                      <p className="text-sm text-gray-600">Location</p>
                      <p className="font-medium text-gray-900">{selectedUser.location}</p>
                    </div>
                  )}
                  {selectedUser.profession && (
                    <div>
                      <p className="text-sm text-gray-600">Profession</p>
                      <p className="font-medium text-gray-900">{selectedUser.profession}</p>
                    </div>
                  )}
                  {selectedUser.academic_background && (
                    <div>
                      <p className="text-sm text-gray-600">Education</p>
                      <p className="font-medium text-gray-900">{selectedUser.academic_background}</p>
                    </div>
                  )}
                  {selectedUser.marital_status && (
                    <div>
                      <p className="text-sm text-gray-600">Marital Status</p>
                      <p className="font-medium text-gray-900 capitalize">{selectedUser.marital_status}</p>
                    </div>
                  )}
                </div>
              </section>

              {/* Physical Attributes */}
              {(selectedUser.height || selectedUser.weight || selectedUser.blood_group) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 2a1 1 0 00-1 1v1a1 1 0 002 0V3a1 1 0 00-1-1zM4 4h3a3 3 0 006 0h3a2 2 0 012 2v9a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm2.5 7a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm2.45 4a2.5 2.5 0 10-4.9 0h4.9zM12 9a1 1 0 100 2h3a1 1 0 100-2h-3zm-1 4a1 1 0 011-1h2a1 1 0 110 2h-2a1 1 0 01-1-1z" clipRule="evenodd" />
                    </svg>
                    Physical Attributes & Health
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg">
                    {selectedUser.height && (
                      <div>
                        <p className="text-sm text-gray-600">Height</p>
                        <p className="font-medium text-gray-900">{selectedUser.height} cm</p>
                      </div>
                    )}
                    {selectedUser.weight && (
                      <div>
                        <p className="text-sm text-gray-600">Weight</p>
                        <p className="font-medium text-gray-900">{selectedUser.weight} kg</p>
                      </div>
                    )}
                    {selectedUser.blood_group && (
                      <div>
                        <p className="text-sm text-gray-600">Blood Group</p>
                        <p className="font-medium text-gray-900">{selectedUser.blood_group}</p>
                      </div>
                    )}
                    {selectedUser.overall_health_status && (
                      <div className="col-span-2 md:col-span-3">
                        <p className="text-sm text-gray-600">Health Status</p>
                        <p className="font-medium text-gray-900 capitalize">{selectedUser.overall_health_status}</p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Lifestyle & Habits */}
              {(selectedUser.dietary_preference || selectedUser.smoking_habit || selectedUser.alcohol_consumption) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Lifestyle & Habits
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg">
                    {selectedUser.dietary_preference && (
                      <div>
                        <p className="text-sm text-gray-600">Diet</p>
                        <p className="font-medium text-gray-900 capitalize">{selectedUser.dietary_preference}</p>
                      </div>
                    )}
                    {selectedUser.smoking_habit && (
                      <div>
                        <p className="text-sm text-gray-600">Smoking</p>
                        <p className="font-medium text-gray-900 capitalize">{selectedUser.smoking_habit}</p>
                      </div>
                    )}
                    {selectedUser.alcohol_consumption && (
                      <div>
                        <p className="text-sm text-gray-600">Alcohol</p>
                        <p className="font-medium text-gray-900 capitalize">{selectedUser.alcohol_consumption}</p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Interests & Hobbies */}
              {(selectedUser.interests || selectedUser.hobbies) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    Interests & Hobbies
                  </h3>
                  <div className="bg-gradient-to-br from-pink-50 to-purple-50 p-4 rounded-lg space-y-3">
                    {selectedUser.interests && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Interests</p>
                        <div className="flex flex-wrap gap-2">
                          {selectedUser.interests.split(',').map((interest, idx) => (
                            <span key={idx} className="px-3 py-1 bg-white rounded-full text-sm text-pink-700 border border-pink-200 shadow-sm">
                              {interest.trim()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {selectedUser.hobbies && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Hobbies</p>
                        <p className="text-gray-900">{selectedUser.hobbies}</p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Partner Preferences */}
              {(selectedUser.preferred_age_min || selectedUser.living_with_in_laws || selectedUser.willing_to_relocate !== null) && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                    </svg>
                    Partner Preferences
                  </h3>
                  <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                    {selectedUser.preferred_age_min && selectedUser.preferred_age_max && (
                      <div>
                        <p className="text-sm text-gray-600">Preferred Age Range</p>
                        <p className="font-medium text-gray-900">{selectedUser.preferred_age_min} - {selectedUser.preferred_age_max} years</p>
                      </div>
                    )}
                    {selectedUser.living_with_in_laws && (
                      <div>
                        <p className="text-sm text-gray-600">Living with In-Laws</p>
                        <p className="font-medium text-gray-900 capitalize">{selectedUser.living_with_in_laws}</p>
                      </div>
                    )}
                    {selectedUser.willing_to_relocate !== null && (
                      <div>
                        <p className="text-sm text-gray-600">Willing to Relocate</p>
                        <p className="font-medium text-gray-900">{selectedUser.willing_to_relocate ? 'Yes' : 'No'}</p>
                      </div>
                    )}
                  </div>
                </section>
              )}
              </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gray-50 p-6 rounded-b-2xl border-t border-gray-200">
              <button
                onClick={() => setSelectedUser(null)}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white py-3 px-6 rounded-lg font-medium transition-all shadow-md hover:shadow-lg"
              >
                Close Overview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FindMatches;
