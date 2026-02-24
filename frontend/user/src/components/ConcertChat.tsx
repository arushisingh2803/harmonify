import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

export default function ConcertChat() {
  const { concertId } = useParams<{ concertId: string }>();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");

  const username = localStorage.getItem("spotify_username") || "Anonymous";

  useEffect(() => {
    if (!concertId) return;

    console.log("Connecting to room:", concertId);

    const ws = new WebSocket(
      `ws://localhost:8000/ws/concerts/${concertId}/`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [concertId]);

  function sendMessage() {
    if (!socket || input.trim() === "") return;

    socket.send(
      JSON.stringify({
        message: input,
        username: username,
      })
    );

    setInput("");
  }

  if (!concertId) {
    return <h2>Invalid concert</h2>;
  }

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Concert Chat</h2>

      <div
        style={{
          border: "1px solid #ccc",
          padding: "1rem",
          height: "300px",
          overflowY: "auto",
          marginBottom: "1rem",
        }}
      >
        {messages.map((msg, index) => (
          <div key={index}>
            <strong>{msg.username}: </strong>
            {msg.message}
          </div>
        ))}
      </div>

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type a message..."
      />

      <button onClick={sendMessage}>
        Send
      </button>
    </div>
  );
}