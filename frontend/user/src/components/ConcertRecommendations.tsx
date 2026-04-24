import { useEffect, useRef, useState } from "react";
import "./style/ConcertRecommendations.css";

interface Concert {
  artist_name:     string;
  event_name:      string;
  venue:           string;
  city:            string;
  date:            string;
  url?:            string;
  image_url?:      string;
  ticketmaster_id: string;
}
interface Props {
  activeConcertId:  string | null;
  onJoinChat:       (id: string) => void;
  onCloseChat:      () => void;
}

export default function ConcertRecommendations({
  activeConcertId,
  onJoinChat,
  onCloseChat,
}: Props) {
  const [concerts, setConcerts] = useState<Concert[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput]       = useState("");
  const socketRef                = useRef<WebSocket | null>(null);
  const messagesEndRef           = useRef<HTMLDivElement>(null);

  const username = localStorage.getItem("spotify_username") || "Anonymous";
  const userId   = localStorage.getItem("harmonify_user_id") || "";

  // fetch concerts
  useEffect(() => {
    if (!userId) {
      setError("User not authenticated");
      setLoading(false);
      return;
    }
    fetch(`http://localhost:8000/concerts-recommendations/?user_id=${userId}`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch");
        return res.json();
      })
      .then(data => {
        setConcerts((data.concerts ?? []).map((c: any) => ({
          artist_name:     c.artist,
          event_name:      c.event_name,
          venue:           c.venue,
          city:            c.city,
          date:            c.date,
          url:             c.url,
          image_url:       c.image_url,
          ticketmaster_id: c.ticketmaster_id,
        })));
      })
      .catch(() => setError("Could not load concert recommendations"))
      .finally(() => setLoading(false));
  }, []);

  // websocket — connect when activeConcertId changes
  useEffect(() => {
    if (!activeConcertId) {
      socketRef.current?.close();
      socketRef.current = null;
      setMessages([]);
      return;
    }

    setMessages([]);
    const ws = new WebSocket(`ws://localhost:8000/ws/concerts/${activeConcertId}/`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, data]);
    };
    ws.onopen  = () => console.log("WebSocket connected");
    ws.onerror = (e) => console.error("WebSocket error:", e);
    ws.onclose = () => console.log("WebSocket closed");
    socketRef.current = ws;

    return () => ws.close();
  }, [activeConcertId]);

  // auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function sendMessage() {
    const ws = socketRef.current;
    if (!ws || input.trim() === "") return;
    ws.send(JSON.stringify({
      message:  input,
      username: username,
      user_id:  userId,
    }));
    setInput("");
  }

  const activeConcert = concerts.find(c => c.ticketmaster_id === activeConcertId);

  return (
    <div className={`concert-wrapper ${activeConcertId ? "with-chat" : ""}`}>

      {/* Concert list */}
      <div className="concert-list">
        <div className="header">
          <h1>Concert Recommendations</h1>
        </div>

        {loading && <p>Loading concerts… 🎶</p>}
        {error   && <p className="error">{error}</p>}
        {!loading && !error && concerts.length === 0 && (
          <p>No upcoming concerts found for your top artists.</p>
        )}

        <div className="cards">
          {concerts.map(concert => (
            <div
              key={concert.ticketmaster_id}
              className={`card ${activeConcertId === concert.ticketmaster_id ? "active" : ""}`}
            >
              {concert.image_url ? (
                <img
                  src={concert.image_url}
                  alt={concert.event_name}
                  className="card-image"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              ) : (
                <div className="image-placeholder" />
              )}

              <p className="text">
                <strong>{concert.artist_name}</strong><br />
                {concert.venue}, {concert.city}<br />
                {concert.date}
              </p>

              <div className="card-actions">
                {concert.url && (
                  <a href={concert.url} target="_blank" rel="noopener noreferrer">
                    <button className="chat-btn">View Event</button>
                  </a>
                )}
                <button
                  className="chat-btn primary"
                  onClick={() => onJoinChat(concert.ticketmaster_id)}
                >
                  Join Chat 💬
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat panel */}
      {activeConcertId && (
        <div className="chat-panel">
          <div className="chat-header">
            <span>
              {activeConcert
                ? `${activeConcert.artist_name} — Chat`
                : "Concert Chat 🎶"}
            </span>
            <button className="close-btn" onClick={onCloseChat}>✕</button>
          </div>

          <div className="chat-messages">
            {messages.length === 0 && (
              <p className="chat-empty">No messages yet. Start the conversation!</p>
            )}
            {messages.map((msg, i) => {
              const isMe = String(msg.user_id) === String(userId);
              return (
                <div key={i} className={`message ${isMe ? "me" : "other"}`}>
                  <strong>{msg.username}</strong>
                  <span>{msg.message}</span>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a message..."
              onKeyDown={e => e.key === "Enter" && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
          </div>
        </div>
      )}
    </div>
  );
}