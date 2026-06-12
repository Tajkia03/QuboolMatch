import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdmin } from '../context/AdminContext';
import VerifyUsers from '../components/admin/VerifyUsers';
import AdminStats from '../components/admin/AdminStats';
import UserReports from '../components/admin/UserReports';

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('stats');
  const { adminLogout } = useAdmin();
  const navigate = useNavigate();

  const handleLogout = () => {
    adminLogout();
    navigate('/admin-login');
  };

  const sidebarItems = [
    { id: 'stats', label: 'Dashboard', icon: '📊' },
    { id: 'verify-users', label: 'Verify Users', icon: '👥' },
    { id: 'user-reports', label: 'User Reports', icon: '📝' },
    { id: 'users', label: 'All Users', icon: '👤' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'stats':
        return <AdminStats />;
      case 'verify-users':
        return <VerifyUsers />;
      case 'user-reports':
        return <UserReports />;
      case 'users':
        return <div className="p-6">All Users component coming soon...</div>;
      case 'settings':
        return <div className="p-6">Settings component coming soon...</div>;
      default:
        return <AdminStats />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="flex items-center justify-center h-16 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">Q</span>
            </div>
            <span className="text-xl font-bold text-gray-800">Admin Panel</span>
          </div>
        </div>
        
        <nav className="mt-8">
          <div className="px-4 space-y-2">
            {sidebarItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-red-50 text-red-700 border-r-2 border-red-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span className="mr-3 text-lg">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </nav>

        <div className="absolute bottom-0 w-64 p-4 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-4 py-2 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="mr-3 text-lg">🚪</span>
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between px-6 py-4">
            <h1 className="text-2xl font-semibold text-gray-800">
              {sidebarItems.find(item => item.id === activeTab)?.label || 'Dashboard'}
            </h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, Admin</span>
              <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
                <span className="text-white font-bold text-sm">A</span>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;