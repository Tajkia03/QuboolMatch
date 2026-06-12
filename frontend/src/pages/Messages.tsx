import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { API_BASE_URL, getAccessToken, messageApi, trustSafetyApi } from '../services/api';

type ChatUser = {
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

type Message = {
  id: string;
  from_user_id: string;
  to_user_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
  updated_at: string;
};

type Conversation = {
  user: ChatUser;
  last_message: Message;
  unread_count: number;
  block_status?: {
    blocked_by_me: boolean;
    blocked_me: boolean;
    blocked: boolean;
  };
};

const getCurrentUserIdFromToken = (): string | null => {
  try {
    const token = getAccessToken();
    if (!token) {
      return null;
    }
    const parts = token.split('.');
    if (parts.length < 2) {
      return null;
    }
    const payload = JSON.parse(atob(parts[1]));
    return payload?.user_id || null;
  } catch {
    return null;
  }
};

const Messages: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeUserId, setActiveUserId] = useState<string | null>(null);
  const [activeUserName, setActiveUserName] = useState<string>('New match');
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const activeUserRef = useRef<string | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);

  const activeConversation = useMemo(
    () => conversations.find((conv) => conv.user.id === activeUserId) ?? null,
    [conversations, activeUserId]
  );

  const isBlockedByMe = Boolean(activeConversation?.block_status?.blocked_by_me);
  const isBlockedByThem = Boolean(activeConversation?.block_status?.blocked_me);
  const isBlockedEitherWay = isBlockedByMe || isBlockedByThem;

  const renderVerificationBadges = (user: ChatUser | null) => {
    if (!user || (!user.nid_verified && !user.photo_verified)) {
      return null;
    }

    return (
      <div className="flex flex-wrap gap-2 mt-1">
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

  const handleReportActive = async () => {
    if (!activeConversation) return;
    const reason = window.prompt('Why are you reporting this user? (e.g., harassment, scam, spam)');
    if (!reason || !reason.trim()) return;
    const details = window.prompt('Any additional details? (optional)');
    try {
      await trustSafetyApi.reportUser(activeConversation.user.id, reason.trim(), details?.trim() || undefined, 'messages');
      alert('Report submitted. Thank you for helping keep the community safe.');
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : 'Failed to submit report';
      alert(msg);
    }
  };

  const handleBlockActive = async () => {
    if (!activeConversation) return;
    if (!window.confirm(`Block ${activeConversation.user.name}? You will no longer see each other.`)) return;
    try {
      await trustSafetyApi.blockUser(activeConversation.user.id);
      await loadConversations();
      if (activeUserId) {
        await loadThread(activeUserId);
      }
      alert(`${activeConversation.user.name} has been blocked.`);
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : 'Failed to block user';
      alert(msg);
    }
  };

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      setLoadingConversations(true);
      setError(null);
      const response = await messageApi.getConversations();
      const nextConversations: Conversation[] = response.conversations ?? [];
      setConversations(nextConversations);

      const requestedUserId = searchParams.get('user');
      const requestedName = searchParams.get('name');
      const currentUserId = getCurrentUserIdFromToken();

      if (requestedUserId && currentUserId && requestedUserId === currentUserId) {
        if (!activeUserId && nextConversations.length > 0) {
          setActiveUserId(nextConversations[0].user.id);
        }
        setError('Invalid chat target detected. Please select another user.');
        return;
      }

      if (requestedUserId && nextConversations.some((conv) => conv.user.id === requestedUserId)) {
        setActiveUserId(requestedUserId);
      } else if (requestedUserId) {
        setActiveUserId(requestedUserId);
        setActiveUserName(requestedName || 'New match');
      } else if (!activeUserId && nextConversations.length > 0) {
        setActiveUserId(nextConversations[0].user.id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load conversations';
      setError(msg);
    } finally {
      setLoadingConversations(false);
    }
  };

  const loadThread = async (otherUserId: string) => {
    try {
      setLoadingMessages(true);
      setError(null);
      const response = await messageApi.getThread(otherUserId, 200);
      const threadMessages: Message[] = response.messages ?? [];
      setMessages(threadMessages);
      await messageApi.markThreadAsRead(otherUserId);
      setConversations((prev) =>
        prev.map((conv) => (conv.user.id === otherUserId ? { ...conv, unread_count: 0 } : conv))
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load messages';
      setError(msg);
    } finally {
      setLoadingMessages(false);
    }
  };

  const connectSocket = () => {
    const token = getAccessToken();
    if (!token) return;

    const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
    const socket = new WebSocket(`${wsUrl}/api/ws/messages?token=${encodeURIComponent(token)}`);

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string; message?: Message };
        if (payload.type !== 'new_message' || !payload.message) return;

        const msg = payload.message;
        void loadConversations();

        const currentActive = activeUserRef.current;
        if (currentActive && (msg.from_user_id === currentActive || msg.to_user_id === currentActive)) {
          setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
          if (msg.from_user_id === currentActive) {
            void messageApi.markThreadAsRead(currentActive);
          }
        }
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    wsRef.current = socket;
  };

  useEffect(() => {
    void loadConversations();
    connectSocket();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (!activeUserId) return;
    activeUserRef.current = activeUserId;
    const params: Record<string, string> = { user: activeUserId };
    const currentName = activeConversation?.user.name || searchParams.get('name') || activeUserName;
    if (currentName) {
      params.name = currentName;
    }
    setSearchParams(params);
    void loadThread(activeUserId);
  }, [activeUserId]);

  useEffect(() => {
    if (!activeUserId) {
      activeUserRef.current = null;
    }
  }, [activeUserId]);

  useEffect(() => {
    if (activeConversation?.user?.name) {
      setActiveUserName(activeConversation.user.name);
    }
  }, [activeConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!activeUserId || !draft.trim()) return;
    if (isBlockedEitherWay) {
      setError(isBlockedByThem ? 'This user blocked you. You can view the conversation but cannot send messages.' : 'Unblock this user before sending messages.');
      return;
    }

    try {
      setSending(true);
      setError(null);
      const content = draft.trim();
      setDraft('');
      const response = await messageApi.sendMessage(activeUserId, content);
      const sentMessage = response.message as Message;
      setMessages((prev) => [...prev, sentMessage]);

      setConversations((prev) =>
        prev
          .map((conv) =>
            conv.user.id === activeUserId
              ? { ...conv, last_message: sentMessage }
              : conv
          )
          .sort((a, b) => new Date(b.last_message.created_at).getTime() - new Date(a.last_message.created_at).getTime())
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send message';
      setError(msg);
    } finally {
      setSending(false);
    }
  };

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="bg-white rounded-xl shadow-lg p-4 md:p-6">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-800 mb-5">Messages</h1>

          {error && (
            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 min-h-[520px]">
            <div className="md:col-span-1 border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 font-semibold text-gray-700">
                Conversations
              </div>
              <div className="max-h-[460px] overflow-y-auto">
                {loadingConversations ? (
                  <div className="p-4 text-sm text-gray-500">Loading...</div>
                ) : conversations.length === 0 ? (
                  <div className="p-4 text-sm text-gray-500">No conversations yet.</div>
                ) : (
                  conversations.map((conv) => (
                    <button
                      key={conv.user.id}
                      onClick={() => setActiveUserId(conv.user.id)}
                      className={`w-full px-4 py-3 text-left border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                        activeUserId === conv.user.id ? 'bg-indigo-50' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {conv.user.profile_picture ? (
                          <img src={conv.user.profile_picture} alt={conv.user.name} className="h-10 w-10 rounded-full object-cover" />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-semibold">
                            {conv.user.name.charAt(0)}
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold text-gray-800 truncate">{conv.user.name}</div>
                          <div className="text-xs text-gray-500 truncate">{conv.last_message.content}</div>
                          {conv.block_status?.blocked_by_me && (
                            <div className="mt-1 inline-flex rounded-full bg-red-100 text-red-700 text-[11px] font-medium px-2 py-0.5">
                              Blocked
                            </div>
                          )}
                        </div>
                        {conv.unread_count > 0 && (
                          <span className="bg-red-600 text-white text-xs font-bold rounded-full px-2 py-0.5">
                            {conv.unread_count}
                          </span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="md:col-span-2 border border-gray-200 rounded-lg overflow-hidden flex flex-col">
              {activeUserId ? (
                <>
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-gray-800">{activeConversation?.user.name || activeUserName}</div>
                      <div className="text-xs text-gray-500">{activeConversation?.user.religion ?? 'Matched user'}</div>
                      {renderVerificationBadges(activeConversation?.user ?? null)}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {isBlockedByMe && (
                          <div className="inline-flex rounded-full bg-red-100 text-red-700 text-xs font-medium px-2 py-1">
                            Blocked by you
                          </div>
                        )}
                        {isBlockedByThem && (
                          <div className="inline-flex rounded-full bg-amber-100 text-amber-800 text-xs font-medium px-2 py-1">
                            This user blocked you
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleReportActive}
                        className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md"
                      >
                        Report
                      </button>
                      <button
                        onClick={handleBlockActive}
                        className="px-3 py-1.5 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded-md"
                      >
                        {isBlockedByMe ? 'Blocked' : 'Block'}
                      </button>
                    </div>
                  </div>

                  <div className="flex-1 max-h-[390px] overflow-y-auto px-4 py-4 bg-white space-y-3">
                    {loadingMessages ? (
                      <div className="text-sm text-gray-500">Loading messages...</div>
                    ) : messages.length === 0 ? (
                      <div className="text-sm text-gray-500">No messages yet. Start the conversation.</div>
                    ) : (
                      messages.map((msg) => {
                        const isMine = msg.to_user_id === activeUserId;
                        return (
                          <div key={msg.id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                            <div
                              className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                                isMine ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              <div>{msg.content}</div>
                              <div className={`mt-1 text-[11px] ${isMine ? 'text-indigo-100' : 'text-gray-500'}`}>
                                {formatTime(msg.created_at)}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                    <div ref={endOfMessagesRef} />
                  </div>

                  <div className="border-t border-gray-200 p-3 bg-gray-50">
                    {isBlockedByMe && (
                      <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 flex items-center justify-between gap-3">
                        <span>You blocked this person. Unblock them to resume chatting.</span>
                        <button
                          onClick={async () => {
                            if (!activeConversation) return;
                            try {
                              await trustSafetyApi.unblockUser(activeConversation.user.id);
                              await loadConversations();
                              if (activeUserId) {
                                await loadThread(activeUserId);
                              }
                            } catch (err: any) {
                              alert(err instanceof Error ? err.message : 'Failed to unblock user');
                            }
                          }}
                          className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-red-700 border border-red-200 hover:bg-red-100"
                        >
                          Unblock
                        </button>
                      </div>
                    )}
                    {isBlockedByThem && (
                      <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                        This user blocked you. You can still view the conversation for transparency, but you cannot send new messages.
                      </div>
                    )}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={draft}
                        maxLength={1000}
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            void sendMessage();
                          }
                        }}
                        placeholder="Type a message..."
                        disabled={isBlockedEitherWay}
                        className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-gray-100 disabled:text-gray-500"
                      />
                      <button
                        onClick={() => void sendMessage()}
                        disabled={sending || !draft.trim() || isBlockedEitherWay}
                        className="rounded-md bg-indigo-600 text-white px-4 py-2 text-sm font-medium disabled:opacity-60"
                      >
                        {sending ? 'Sending...' : 'Send'}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                  Select a conversation to start chatting.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Messages;
