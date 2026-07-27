import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { interestApi, notificationApi } from "../services/api";

interface Notification {
  id: string;
  type: "interest_received" | "interest_accepted" | "interest_rejected" | "new_message" | "system";
  from_user_id?: string;
  from_user?: {
    id: string;
    name: string;
    age: number;
    profile_picture: string | null;
  };
  message: string;
  created_at: string;
  is_read: boolean;
  related_id?: string;
  interest_action_status?: "accepted" | "rejected";
}

type InterestActionStatus = "accepted" | "rejected";

const HANDLED_INTEREST_NOTIFICATION_KEY = "handledInterestNotifications";

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

const applyHandledInterestStatus = (items: Notification[]): Notification[] => {
  const handledMap = readHandledInterestNotificationMap();
  return items.map((item) => {
    const handledStatus = handledMap[item.id] || (item.related_id ? handledMap[item.related_id] : undefined);
    if (item.type !== "interest_received" || !handledStatus) {
      return item;
    }

    const suffix = handledStatus === "accepted"
      ? "(You accepted this request)"
      : "(You rejected this request)";
    const nextMessage = item.message.includes(suffix) ? item.message : `${item.message} ${suffix}`;

    return {
      ...item,
      is_read: true,
      interest_action_status: handledStatus,
      message: nextMessage,
    };
  });
};

const NotificationDropdown: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const dropdownRef = useRef<HTMLDivElement>(null);

  const toggleDropdown = async () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      await fetchNotifications();
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await notificationApi.getNotifications();
      const items = applyHandledInterestStatus(response.notifications || []);
      setNotifications(items);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId: string) => {
    const target = notifications.find((n) => n.id === notificationId);
    if (!target || target.is_read) {
      return;
    }

    setNotifications((prev) => prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n)));
    try {
      await notificationApi.markAsRead(notificationId);
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
      await fetchNotifications();
    }
  };

  const handleNotificationClick = async (notification: Notification) => {
    await markAsRead(notification.id);

    if (notification.type === "interest_received") {
      setIsOpen(false);
      navigate("/interest-requests");
      return;
    }

    if (notification.type === "interest_accepted" && notification.from_user_id) {
      const userName = notification.from_user?.name ?? "Match";
      setIsOpen(false);
      navigate(`/messages?user=${encodeURIComponent(notification.from_user_id)}&name=${encodeURIComponent(userName)}`);
      return;
    }

    if (notification.type === "new_message" && notification.from_user_id) {
      const userName = notification.from_user?.name ?? "User";
      setIsOpen(false);
      navigate(`/messages?user=${encodeURIComponent(notification.from_user_id)}&name=${encodeURIComponent(userName)}`);
      return;
    }

    setIsOpen(false);
    navigate("/notifications");
  };

  const handleInterestAction = async (notification: Notification, action: "accept" | "reject") => {
    if (!notification.related_id) {
      return;
    }

    setActionLoading((prev) => ({ ...prev, [notification.id]: true }));
    try {
      if (action === "accept") {
        await interestApi.acceptInterest(notification.related_id);
      } else {
        await interestApi.rejectInterest(notification.related_id);
      }

      const handledStatus: InterestActionStatus = action === "accept" ? "accepted" : "rejected";
      const existingMap = readHandledInterestNotificationMap();
      writeHandledInterestNotificationMap({
        ...existingMap,
        [notification.id]: handledStatus,
        ...(notification.related_id ? { [notification.related_id]: handledStatus } : {}),
      });

      setNotifications((prev) =>
        prev.map((item) => {
          if (item.id !== notification.id) {
            return item;
          }
          return {
            ...item,
            is_read: true,
            interest_action_status: handledStatus,
            message:
              action === "accept"
                ? `${item.message} (You accepted this request)`
                : `${item.message} (You rejected this request)`,
          };
        })
      );

      await markAsRead(notification.id);
    } catch (error) {
      console.error(`Failed to ${action} interest:`, error);
      await fetchNotifications();
    } finally {
      setActionLoading((prev) => ({ ...prev, [notification.id]: false }));
    }
  };

  useEffect(() => {
    void fetchNotifications();
    
    // Close dropdown when clicking outside
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes}m ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours}h ago`;
    } else {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days}d ago`;
    }
  };

  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        className="relative p-1 text-gray-700 hover:text-indigo-600 focus:outline-none"
        onClick={toggleDropdown}
        aria-label="Notifications"
      >
        <svg 
          className="h-6 w-6" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1.5} 
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg overflow-hidden z-50">
          <div className="py-2">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold text-gray-700">Notifications</h3>
                <Link 
                  to="/notifications" 
                  className="text-xs text-indigo-600 hover:text-indigo-800"
                  onClick={() => setIsOpen(false)}
                >
                  View all
                </Link>
              </div>
            </div>

            <div className="max-h-72 overflow-y-auto">
              {loading ? (
                <div className="flex justify-center items-center py-4">
                  <div className="animate-spin h-5 w-5 border-2 border-indigo-500 rounded-full border-t-transparent"></div>
                </div>
              ) : notifications.length > 0 ? (
                <div>
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`border-b border-gray-100 ${!notification.is_read ? 'bg-blue-50' : ''}`}
                    >
                      <button
                        type="button"
                        className="w-full text-left block px-4 py-3 hover:bg-gray-50 transition-colors"
                        onClick={() => void handleNotificationClick(notification)}
                      >
                      <div className="flex items-center">
                        {notification.from_user?.profile_picture && (
                          <div className="flex-shrink-0 mr-3">
                            <img
                              className="h-10 w-10 rounded-full object-cover"
                              src={notification.from_user.profile_picture}
                              alt={notification.from_user.name || "User"}
                            />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm ${!notification.is_read ? 'font-semibold' : 'font-normal'} text-gray-900 truncate`}>
                            {notification.message}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatTimestamp(notification.created_at)}
                          </p>
                        </div>
                        {!notification.is_read && (
                          <div className="ml-2 flex-shrink-0">
                            <span className="inline-block h-2 w-2 rounded-full bg-indigo-600"></span>
                          </div>
                        )}
                      </div>
                      </button>
                      {notification.type === "interest_received" && notification.related_id && !notification.interest_action_status && (
                        <div className="px-4 pb-3 flex gap-2">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleInterestAction(notification, "accept");
                            }}
                            disabled={Boolean(actionLoading[notification.id])}
                            className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
                          >
                            {actionLoading[notification.id] ? "Working..." : "Confirm"}
                          </button>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleInterestAction(notification, "reject");
                            }}
                            disabled={Boolean(actionLoading[notification.id])}
                            className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-4 py-6 text-center text-sm text-gray-500">
                  No new notifications
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;
