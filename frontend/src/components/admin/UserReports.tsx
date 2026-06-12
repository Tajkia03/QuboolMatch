import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../../services/api';

type AdminUserSummary = {
  id: string;
  name: string | null;
  email: string | null;
  is_admin: boolean;
};

type UserReport = {
  id: string;
  reporter: AdminUserSummary;
  reported: AdminUserSummary;
  reason: string;
  details: string | null;
  context: string | null;
  status: 'pending' | 'resolved' | 'dismissed' | string;
  created_at: string | null;
};

type UserReportsResponse = {
  reports: UserReport[];
  total_count: number;
};

const statusFilters: Array<'all' | 'pending' | 'resolved' | 'dismissed'> = ['all', 'pending', 'resolved', 'dismissed'];

const UserReports: React.FC = () => {
  const [reports, setReports] = useState<UserReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'pending' | 'resolved' | 'dismissed'>('pending');
  const [updatingReportId, setUpdatingReportId] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    void fetchReports();
  }, [activeFilter]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      setError('');
      const token = localStorage.getItem('adminAccessToken');
      const params = new URLSearchParams({ skip: '0', limit: '100' });
      if (activeFilter !== 'all') {
        params.set('status', activeFilter);
      }

      const response = await fetch(`${API_BASE_URL}/admin/reports?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user reports');
      }

      const data: UserReportsResponse = await response.json();
      setReports(data.reports ?? []);
      setTotalCount(data.total_count ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch user reports');
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (reportId: string, status: 'resolved' | 'dismissed') => {
    try {
      setUpdatingReportId(reportId);
      const token = localStorage.getItem('adminAccessToken');
      const response = await fetch(`${API_BASE_URL}/admin/reports/${reportId}/status`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error('Failed to update report status');
      }

      setReports((prev) => prev.map((report) => (report.id === reportId ? { ...report, status } : report)));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update report status');
    } finally {
      setUpdatingReportId(null);
    }
  };

  const formatDateTime = (iso: string | null) => {
    if (!iso) return 'Unknown date';
    return new Date(iso).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const statusBadgeClasses: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    dismissed: 'bg-gray-200 text-gray-800',
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">User Reports</h2>
          <p className="text-gray-600 mt-1">
            Review user feedback and handle issues from one place
          </p>
        </div>
        <div className="text-sm text-gray-600">
          {totalCount} report{totalCount === 1 ? '' : 's'} found
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {statusFilters.map((status) => (
          <button
            key={status}
            onClick={() => setActiveFilter(status)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              activeFilter === status
                ? 'bg-red-600 text-white'
                : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center text-gray-600">
          Loading user reports...
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md">
          {error}
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="text-6xl mb-4">📝</div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">No reports to review</h3>
          <p className="text-gray-600">Reports will appear here when users submit feedback.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <div key={report.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-3 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClasses[report.status] || 'bg-gray-100 text-gray-700'}`}>
                      {report.status}
                    </span>
                    <span className="text-xs text-gray-500">{formatDateTime(report.created_at)}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <div className="rounded-md bg-gray-50 p-3">
                      <div className="text-gray-500 text-xs uppercase tracking-wide">Reported by</div>
                      <div className="font-semibold text-gray-800 mt-1">{report.reporter.name || 'Unknown user'}</div>
                      <div className="text-gray-600">{report.reporter.email || report.reporter.id}</div>
                    </div>
                    <div className="rounded-md bg-gray-50 p-3">
                      <div className="text-gray-500 text-xs uppercase tracking-wide">Reported user</div>
                      <div className="font-semibold text-gray-800 mt-1">{report.reported.name || 'Unknown user'}</div>
                      <div className="text-gray-600">{report.reported.email || report.reported.id}</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Reason</div>
                    <div className="font-medium text-gray-800">{report.reason}</div>
                  </div>

                  {report.details && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Details</div>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap">{report.details}</div>
                    </div>
                  )}

                  {report.context && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Context</div>
                      <div className="text-sm text-gray-700">{report.context}</div>
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 lg:flex-col lg:w-44">
                  {report.status === 'pending' ? (
                    <>
                      <button
                        onClick={() => void updateStatus(report.id, 'resolved')}
                        disabled={updatingReportId === report.id}
                        className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                      >
                        {updatingReportId === report.id ? 'Saving...' : 'Resolve'}
                      </button>
                      <button
                        onClick={() => void updateStatus(report.id, 'dismissed')}
                        disabled={updatingReportId === report.id}
                        className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300 disabled:opacity-60"
                      >
                        Dismiss
                      </button>
                    </>
                  ) : (
                    <div className="text-sm text-gray-500">
                      This report has already been marked as {report.status}.
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UserReports;