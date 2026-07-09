import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../services/api';

interface PendingUser {
  id: string;
  name?: string | null;
  age?: number | null;
  date_of_birth?: string | null;
  nid?: string | null;
  email: string;
  verification_status: string;
  guardian_verification_status: string;
  has_nid_image: boolean;
  nid_image_filename: string | null;
  verification_notes: string | null;
  created_at: string;
  ocr_name_match_status?: string | null;
  ocr_nid_match?: boolean | null;
  ocr_dob_match?: boolean | null;
  ocr_confirmed?: boolean | null;
  ocr_name?: string | null;
  ocr_father_name?: string | null;
  ocr_mother_name?: string | null;
  ocr_date_of_birth?: string | null;
  ocr_nid_number?: string | null;
  ocr_image_quality?: string | null;
  ocr_warnings?: string[] | null;
}

interface PendingVerificationsResponse {
  pending_verifications: PendingUser[];
}

const VerifyUsers: React.FC = () => {
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [processingUserId, setProcessingUserId] = useState<string | null>(null);
  const [guardianProcessingUserId, setGuardianProcessingUserId] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<PendingUser | null>(null);
  const [isReviewOpen, setIsReviewOpen] = useState(false);

  useEffect(() => {
    fetchPendingUsers();
  }, []);

  const fetchPendingUsers = async () => {
    try {
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/verification/pending`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch pending users');
      }

      const data: PendingVerificationsResponse = await response.json();
      
      // Sort by creation time (most recent first)
      const sortedUsers = data.pending_verifications.sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        return dateB.getTime() - dateA.getTime();
      });
      
      setPendingUsers(sortedUsers);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch pending users');
    } finally {
      setLoading(false);
    }
  };

  const readErrorMessage = async (response: Response, fallback: string) => {
    try {
      const payload = await response.json();
      return payload?.detail || payload?.message || fallback;
    } catch {
      return fallback;
    }
  };

  const handleVerifyUser = async (userId: string) => {
    setProcessingUserId(userId);
    try {
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/verification/approve/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response, 'Failed to verify user'));
      }

      // Remove the user from pending list
      setPendingUsers(prev => prev.filter(user => user.id !== userId));

      // Show success message (you can add a toast notification here)
      alert('User verified successfully!');
      return true;
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to verify user');
      return false;
    } finally {
      setProcessingUserId(null);
    }
  };

  const handleRejectUser = async (userId: string) => {
    const rejectionNotes = prompt('Please enter rejection reason:');
    if (!rejectionNotes) return false;

    setProcessingUserId(userId);
    try {
      const token = localStorage.getItem('adminAccessToken');
      const formData = new FormData();
      formData.append('rejection_notes', rejectionNotes);

      const response = await fetch(`${API_BASE_URL}/verification/reject/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response, 'Failed to reject user'));
      }

      // Remove the user from pending list
      setPendingUsers(prev => prev.filter(user => user.id !== userId));

      // Show success message
      alert('User verification rejected successfully!');
      return true;
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to reject user');
      return false;
    } finally {
      setProcessingUserId(null);
    }
  };

  const handleGuardianApprove = async (userId: string) => {
    setGuardianProcessingUserId(userId);
    try {
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/verification/guardian/approve/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response, 'Failed to approve guardian verification'));
      }

      setPendingUsers(prev => prev.map(user =>
        user.id === userId ? { ...user, guardian_verification_status: 'verified' } : user
      ));

      alert('Guardian verification approved!');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to approve guardian verification');
    } finally {
      setGuardianProcessingUserId(null);
    }
  };

  const handleGuardianReject = async (userId: string) => {
    setGuardianProcessingUserId(userId);
    try {
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/verification/guardian/reject/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response, 'Failed to reject guardian verification'));
      }

      setPendingUsers(prev => prev.map(user =>
        user.id === userId ? { ...user, guardian_verification_status: 'rejected' } : user
      ));

      alert('Guardian verification rejected!');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to reject guardian verification');
    } finally {
      setGuardianProcessingUserId(null);
    }
  };

  const viewNIDImage = async (userId: string) => {
    try {
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/verification/image/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch NID image');
      }

      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);
      
      // Open image in new window
      window.open(imageUrl, '_blank');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to view NID image');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getCredentialCheckLabel = (user: PendingUser) => {
    const nameMatch = user.ocr_name_match_status
      ? ['matched', 'match', 'true', 'yes', 'approved'].includes(user.ocr_name_match_status.toLowerCase())
      : false;
    const nidMatch = Boolean(user.ocr_nid_match);
    const dobMatch = Boolean(user.ocr_dob_match);

    const hasAnyProcessedSignal =
      user.ocr_confirmed !== undefined ||
      user.ocr_name_match_status !== undefined ||
      user.ocr_nid_match !== undefined ||
      user.ocr_dob_match !== undefined;

    if (!hasAnyProcessedSignal) {
      return 'Not Processed';
    }

    const matchedCount = [nameMatch, nidMatch, dobMatch].filter(Boolean).length;

    if (matchedCount === 0) {
      return 'Not Processed';
    }

    return `${matchedCount}/3 Matched`;
  };

  const openReviewDetails = (user: PendingUser) => {
    setSelectedUser(user);
    setIsReviewOpen(true);
  };

  const closeReviewDetails = () => {
    setIsReviewOpen(false);
    setSelectedUser(null);
  };

  const handleApproveComparison = async () => {
    if (!selectedUser) {
      return;
    }

    const success = await handleVerifyUser(selectedUser.id);
    if (success) {
      closeReviewDetails();
    }
  };

  const handleRejectComparison = async () => {
    if (!selectedUser) {
      return;
    }

    const success = await handleRejectUser(selectedUser.id);
    if (success) {
      closeReviewDetails();
    }
  };

  const formatMaybeDate = (value: string | null | undefined) => {
    if (!value) {
      return 'Not available';
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const maskNidNumber = (value: string | null | undefined) => {
    if (!value) {
      return 'Not available';
    }

    const trimmed = value.trim();
    if (!trimmed) {
      return 'Not available';
    }

    return trimmed.replace(/\d(?=\d{4})/g, '*');
  };

  const getComparisonBadge = (value: string | boolean | null | undefined) => {
    if (value === null || value === undefined || value === '') {
      return {
        label: 'Not Available',
        className: 'bg-gray-100 text-gray-700',
      };
    }

    if (typeof value === 'boolean') {
      return value
        ? {
            label: 'Matched',
            className: 'bg-green-100 text-green-800',
          }
        : {
            label: 'Does Not Match',
            className: 'bg-red-100 text-red-800',
          };
    }

    const normalized = value.toLowerCase().trim();

    if (['matched', 'match', 'true', 'yes', 'approved'].includes(normalized)) {
      return {
        label: 'Matched',
        className: 'bg-green-100 text-green-800',
      };
    }

    if (['needs_review', 'needs review', 'review', 'pending', 'partial', 'uncertain'].includes(normalized)) {
      return {
        label: 'Needs Review',
        className: 'bg-yellow-100 text-yellow-800',
      };
    }

    if (['does_not_match', 'does not match', 'not_matched', 'mismatch', 'rejected', 'false', 'no'].includes(normalized)) {
      return {
        label: 'Does Not Match',
        className: 'bg-red-100 text-red-800',
      };
    }

    return {
      label: 'Not Available',
      className: 'bg-gray-100 text-gray-700',
    };
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-gray-600">Loading pending verifications...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Pending User Verifications</h2>
        <p className="text-gray-600 mt-1">
          {pendingUsers.length} users awaiting verification
        </p>
      </div>

      {pendingUsers.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="text-6xl mb-4">✅</div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">All caught up!</h3>
          <p className="text-gray-600">No pending verifications at the moment.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-[1100px] divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  NID Document
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Credential Check
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Guardian Verified
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pendingUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{user.email}</div>
                      <div className="text-sm text-gray-500">
                        Registered: {formatDate(user.created_at)}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.verification_status === 'pending' 
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {user.verification_status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {user.has_nid_image ? (
                      <button
                        onClick={() => viewNIDImage(user.id)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View NID Image
                      </button>
                    ) : (
                        <span className="text-gray-400 text-sm">No image</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col items-start gap-2">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        getCredentialCheckLabel(user) === 'Not Processed'
                          ? 'bg-gray-100 text-gray-700'
                          : getCredentialCheckLabel(user) === '3/3 Matched'
                          ? 'bg-green-100 text-green-800'
                          : getCredentialCheckLabel(user) === '2/3 Matched'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-orange-100 text-orange-800'
                      }`}>
                        {getCredentialCheckLabel(user)}
                      </span>
                      <button
                        type="button"
                        onClick={() => openReviewDetails(user)}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Credential Comparison
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        user.guardian_verification_status === 'verified'
                          ? 'bg-green-100 text-green-800'
                          : user.guardian_verification_status === 'rejected'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {user.guardian_verification_status || 'pending'}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleGuardianApprove(user.id)}
                        disabled={guardianProcessingUserId === user.id || user.guardian_verification_status === 'verified'}
                        className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {guardianProcessingUserId === user.id ? 'Processing...' : 'Yes'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleGuardianReject(user.id)}
                        disabled={guardianProcessingUserId === user.id || user.guardian_verification_status === 'rejected'}
                        className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {guardianProcessingUserId === user.id ? 'Processing...' : 'No'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isReviewOpen && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Credential Comparison</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Compare submitted profile data with OCR output returned by the backend.
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => viewNIDImage(selectedUser.id)}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                View NID Image
              </button>
              <div className="text-sm text-gray-500">
                {selectedUser.email}
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="text-base font-semibold text-gray-800">Full Name</h4>
                      <p className="mt-1 text-sm text-gray-600">
                        Submitted: {selectedUser.name || 'Not available'}
                      </p>
                      <p className="text-sm text-gray-600">
                        OCR: {selectedUser.ocr_name || 'Not available'}
                      </p>
                    </div>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getComparisonBadge(selectedUser.ocr_name_match_status).className}`}>
                      {getComparisonBadge(selectedUser.ocr_name_match_status).label}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="text-base font-semibold text-gray-800">NID Number</h4>
                      <p className="mt-1 text-sm text-gray-600">
                        Submitted: {maskNidNumber(selectedUser.nid)}
                      </p>
                      <p className="text-sm text-gray-600">
                        OCR: {maskNidNumber(selectedUser.ocr_nid_number)}
                      </p>
                    </div>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getComparisonBadge(selectedUser.ocr_nid_match).className}`}>
                      {getComparisonBadge(selectedUser.ocr_nid_match).label}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="text-base font-semibold text-gray-800">Date of Birth / Age</h4>
                      <p className="mt-1 text-sm text-gray-600">
                        Submitted: {formatMaybeDate(selectedUser.date_of_birth)}{selectedUser.age !== null && selectedUser.age !== undefined ? `, Age ${selectedUser.age}` : ''}
                      </p>
                      <p className="text-sm text-gray-600">
                        OCR: {formatMaybeDate(selectedUser.ocr_date_of_birth)}
                      </p>
                    </div>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getComparisonBadge(selectedUser.ocr_dob_match).className}`}>
                      {getComparisonBadge(selectedUser.ocr_dob_match).label}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
              <button
                type="button"
                onClick={handleApproveComparison}
                disabled={processingUserId === selectedUser.id}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {processingUserId === selectedUser.id ? 'Processing...' : 'Approve'}
              </button>
              <button
                type="button"
                onClick={handleRejectComparison}
                disabled={processingUserId === selectedUser.id}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {processingUserId === selectedUser.id ? 'Processing...' : 'Reject'}
              </button>
              <button
                type="button"
                onClick={closeReviewDetails}
                className="rounded-md bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VerifyUsers;
