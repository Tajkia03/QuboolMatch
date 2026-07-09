import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { interestApi, notificationApi } from "../services/api";

// Define notification types from backend
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
  interest_action_status?: 'accepted' | 'rejected';
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

const applyHandledInterestStatus = (items: Notification[]): Notification[] => {
  const handledMap = readHandledInterestNotificationMap();
  return items.map((item) => {
    const handledStatus = handledMap[item.id];
    if (item.type !== 'interest_received' || !handledStatus) {
      return item;
    }

    const suffix = handledStatus === 'accepted'
      ? '(You accepted this request)'
      : '(You rejected this request)';
    const nextMessage = item.message.includes(suffix) ? item.message : `${item.message} ${suffix}`;

    return {
      ...item,
      is_read: true,
      interest_action_status: handledStatus,
      message: nextMessage,
    };
  });
};

const Notifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await notificationApi.getNotifications();
      const items = applyHandledInterestStatus(response.notifications || []);
      setNotifications(items);
      setUnreadCount(response.unread_count);
    } catch (err: any) {
      setError(err.message || 'Failed to load notifications');
      console.error('Error loading notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (id: string) => {
    try {
      await notificationApi.markAsRead(id);
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => 
          notification.id === id ? { ...notification, is_read: true } : notification
        )
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err: any) {
      console.error('Error marking notification as read:', err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications(prevNotifications => 
        prevNotifications.map(notification => ({ ...notification, is_read: true }))
      );
      setUnreadCount(0);
    } catch (err: any) {
      console.error('Error marking all as read:', err);
    }
  };

  const deleteNotification = async (id: string) => {
    if (!window.confirm('Delete this notification?')) return;
    
    try {
      await notificationApi.deleteNotification(id);
      setNotifications(prevNotifications => 
        prevNotifications.filter(notification => notification.id !== id)
      );
      // Recalculate unread count
      const deletedNotif = notifications.find(n => n.id === id);
      if (deletedNotif && !deletedNotif.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err: any) {
      alert('Error deleting notification: ' + err.message);
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    void markAsRead(notification.id);
    
    // Navigate based on notification type
    if (notification.type === "interest_received") {
      navigate(`/interest-requests`);
    } else if (notification.type === "interest_accepted" && notification.from_user_id) {
      const userName = notification.from_user?.name || 'Match';
      navigate(`/messages?user=${encodeURIComponent(notification.from_user_id)}&name=${encodeURIComponent(userName)}`);
    } else if (notification.type === "new_message" && notification.from_user_id) {
      const userName = notification.from_user?.name || 'User';
      navigate(`/messages?user=${encodeURIComponent(notification.from_user_id)}&name=${encodeURIComponent(userName)}`);
    } else if (notification.type === "interest_rejected") {
      navigate(`/interest-requests`);
    }
  };

  const handleInterestAction = async (notification: Notification, action: 'accept' | 'reject') => {
    if (!notification.related_id) {
      return;
    }

    try {
      setActionLoading((prev) => ({ ...prev, [notification.id]: true }));
      if (action === 'accept') {
        await interestApi.acceptInterest(notification.related_id);
      } else {
        await interestApi.rejectInterest(notification.related_id);
      }

      const handledStatus: InterestActionStatus = action === 'accept' ? 'accepted' : 'rejected';
      const existingMap = readHandledInterestNotificationMap();
      writeHandledInterestNotificationMap({
        ...existingMap,
        [notification.id]: handledStatus,
      });

      setNotifications((prevNotifications) =>
        prevNotifications.map((item) => {
          if (item.id !== notification.id) {
            return item;
          }
          return {
            ...item,
            is_read: true,
            interest_action_status: handledStatus,
            message:
              action === 'accept'
                ? `${item.message} (You accepted this request)`
                : `${item.message} (You rejected this request)`,
          };
        })
      );

      await markAsRead(notification.id);
    } catch (err: any) {
      setError(err.message || `Failed to ${action} interest request`);
      await loadNotifications();
    } finally {
      setActionLoading((prev) => ({ ...prev, [notification.id]: false }));
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "interest_received":
        return "♡";
      case "interest_accepted":
        return "✓";
      case "interest_rejected":
        return "×";
      case "system":
        return "!";
      case "new_message":
        return "💬";
      default:
        return "•";
    }
  };

  const getNotificationTone = (type: string) => {
    switch (type) {
      case "interest_received":
        return {
          avatar: "from-[#b95777] to-[#7b3d54]",
          dot: "bg-[#b95777] shadow-[0_0_0_6px_rgba(185,87,119,0.12)]",
          label: "Interest request",
        };
      case "interest_accepted":
        return {
          avatar: "from-[#86b59a] to-[#4c9069]",
          dot: "bg-[#66a47d] shadow-[0_0_0_6px_rgba(134,181,154,0.16)]",
          label: "Accepted",
        };
      case "interest_rejected":
        return {
          avatar: "from-[#d86e8e] to-[#a7485b]",
          dot: "bg-[#c55768] shadow-[0_0_0_6px_rgba(216,110,142,0.14)]",
          label: "Interest update",
        };
      case "system":
        return {
          avatar: "from-[#d9a96f] to-[#a96951]",
          dot: "bg-[#d9a96f] shadow-[0_0_0_6px_rgba(217,169,111,0.16)]",
          label: "System",
        };
      case "new_message":
        return {
          avatar: "from-[#8fa7d7] to-[#6f7bb0]",
          dot: "bg-[#7d8fca] shadow-[0_0_0_6px_rgba(143,167,215,0.16)]",
          label: "Message",
        };
      default:
        return {
          avatar: "from-[#b7aaa6] to-[#7b6b67]",
          dot: "bg-[#b7aaa6] shadow-[0_0_0_6px_rgba(183,170,166,0.15)]",
          label: "Notification",
        };
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-[#fffaf6] via-[#f8e7e4] to-[#fff0dc] py-10">
      <div className="pointer-events-none absolute -left-24 top-24 h-72 w-72 rounded-full bg-[#f0b5c5]/50 blur-2xl" />
      <div className="pointer-events-none absolute -right-20 top-72 h-64 w-64 rounded-full bg-[#e7c28d]/45 blur-2xl" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(123,61,84,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(123,61,84,0.035)_1px,transparent_1px)] bg-[size:42px_42px] [mask-image:radial-gradient(circle_at_center,#000_0_44%,transparent_78%)]" />

      <div className="relative z-[1] mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 overflow-hidden rounded-[2rem] border border-white/70 bg-white/70 p-6 shadow-[0_24px_70px_rgba(123,61,84,0.10)] backdrop-blur-xl sm:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <span className="inline-flex rounded-full border border-white/80 bg-white/70 px-4 py-2 text-xs font-extrabold uppercase tracking-[0.18em] text-[#8c3d5b] shadow-[0_12px_30px_rgba(112,53,75,0.07)]">
                Notification timeline
              </span>
              <h1 className="mt-4 font-heading text-4xl font-bold tracking-[-0.03em] text-[#3b2731] sm:text-5xl">
                Your latest updates
              </h1>
              <p className="mt-3 max-w-2xl leading-7 text-[#73625e]">
                Follow match activity, messages, and system reminders in a clean timeline.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold ${unreadCount > 0 ? 'bg-[#ffeaf0] text-[#8c3d5b]' : 'bg-[#edf8ef] text-[#62715f]'}`}>
                {unreadCount > 0 && <span className="h-2 w-2 rounded-full bg-[#b95777]" />}
                {unreadCount} unread
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="rounded-full bg-gradient-to-r from-[#b95777] to-[#7b3d54] px-5 py-2.5 text-sm font-bold text-white shadow-[0_12px_25px_rgba(136,65,89,0.20)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_30px_rgba(136,65,89,0.28)]"
                >
                  Mark all as read
                </button>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-3xl border border-red-200 bg-red-50/90 p-4 text-sm font-medium text-red-700 shadow-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-[2rem] border border-white/70 bg-white/75 p-16 text-center shadow-[0_24px_70px_rgba(123,61,84,0.10)] backdrop-blur-xl">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-[#f0d3dc] border-t-[#b95777]" />
            <p className="mt-4 font-medium text-[#73625e]">Loading your notifications...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="rounded-[2rem] border border-white/70 bg-white/75 p-12 text-center shadow-[0_24px_70px_rgba(123,61,84,0.10)] backdrop-blur-xl">
            <div className="mx-auto grid h-20 w-20 place-items-center rounded-[1.5rem] bg-[#fff4ed] text-4xl text-[#b95777]">♡</div>
            <h3 className="mt-5 font-heading text-2xl font-bold text-[#3b2731]">You’re all caught up</h3>
            <p className="mt-2 text-sm text-[#73625e]">No notifications right now. Check back later for match updates.</p>
          </div>
        ) : (
          <div className="relative pl-6 sm:pl-8">
            <div className="absolute bottom-6 left-[0.45rem] top-6 w-px bg-gradient-to-b from-[#e7a8bb] via-[#e9d1c3] to-transparent sm:left-[0.6rem]" />

            <div className="space-y-5">
              {notifications.map((notification) => {
                const tone = getNotificationTone(notification.type);

                return (
                  <article
                    key={notification.id}
                    className={`relative rounded-[1.6rem] border p-5 shadow-[0_14px_32px_rgba(123,61,84,0.08)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_22px_45px_rgba(123,61,84,0.14)] ${
                      notification.is_read
                        ? 'border-[#ead9d5] bg-[#fffaf6]/85'
                        : 'border-[#e9a6b9] bg-gradient-to-r from-[#fff2f6] to-[#fffaf6]'
                    }`}
                  >
                    <span className={`absolute -left-[1.9rem] top-8 h-3 w-3 rounded-full sm:-left-[2.15rem] ${notification.is_read ? 'bg-[#cdbbb5]' : tone.dot}`} />

                    <button
                      type="button"
                      className="block w-full text-left"
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex gap-4">
                        <div className="flex-shrink-0">
                          {notification.from_user?.profile_picture ? (
                            <img
                              src={notification.from_user.profile_picture}
                              alt={notification.from_user.name}
                              className="h-14 w-14 rounded-[1.1rem] object-cover shadow-[0_12px_24px_rgba(136,65,89,0.14)]"
                              onError={(e) => {
                                e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(notification.from_user?.name || 'User')}&size=56&background=b95777&color=fff`;
                              }}
                            />
                          ) : (
                            <div className={`grid h-14 w-14 place-items-center rounded-[1.1rem] bg-gradient-to-br ${tone.avatar} text-xl font-black text-white shadow-[0_12px_24px_rgba(136,65,89,0.16)]`}>
                              {getNotificationIcon(notification.type)}
                            </div>
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-white/75 px-3 py-1 text-xs font-extrabold text-[#7b3d54]">
                              {tone.label}
                            </span>
                            {!notification.is_read && (
                              <span className="rounded-full bg-[#ffeaf0] px-3 py-1 text-xs font-bold text-[#8c3d5b]">
                                New
                              </span>
                            )}
                            <span className="text-xs font-medium text-[#9a8a86]">
                              {formatTimestamp(notification.created_at)}
                            </span>
                          </div>

                          <p className={`mt-3 text-sm leading-6 ${notification.is_read ? 'text-[#665956]' : 'font-semibold text-[#3b2731]'}`}>
                            {notification.message}
                          </p>

                          {notification.from_user && (
                            <p className="mt-2 text-xs font-medium text-[#8a7975]">
                              From: {notification.from_user.name}, {notification.from_user.age}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>

                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pl-0 sm:pl-[4.5rem]">
                      {notification.type === 'interest_received' && notification.related_id && !notification.interest_action_status ? (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              void handleInterestAction(notification, 'accept');
                            }}
                            disabled={Boolean(actionLoading[notification.id])}
                            className="rounded-full bg-[#e6f8eb] px-4 py-2 text-sm font-bold text-[#1f6f48] transition hover:bg-[#d7f1df] disabled:opacity-50"
                          >
                            {actionLoading[notification.id] ? 'Processing...' : 'Confirm'}
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              void handleInterestAction(notification, 'reject');
                            }}
                            disabled={Boolean(actionLoading[notification.id])}
                            className="rounded-full bg-[#ffe8eb] px-4 py-2 text-sm font-bold text-[#a43245] transition hover:bg-[#ffdce1] disabled:opacity-50"
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs font-medium text-[#9a8a86]">
                          {notification.is_read ? 'Read notification' : 'Click to open and mark as read'}
                        </span>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteNotification(notification.id);
                        }}
                        className="rounded-full border border-[#ead9d5] bg-white/70 px-3 py-2 text-xs font-bold text-[#8b7470] transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                        title="Delete notification"
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Notifications;
