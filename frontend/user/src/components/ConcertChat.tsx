import { useEffect, useState } from "react";

interface Message {
  user: string;
  message: string;
}

export default function ConcertChat({ concertId }: { concertId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/ws/concerts/${concertId}/`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    setSocket(ws);

    return () => ws.close();
  }, [concertId]);

  const sendMessage = () => {
    if (!socket || !input) return;

    socket.send(
      JSON.stringify({
        user: "User",
        message: input,
      })
    );

    setInput("");
  };

  return (
    <div>
      <h3>Concert Chat</h3>

      <div style={{ height: 200, overflowY: "scroll" }}>
        {messages.map((m, i) => (
          <p key={i}>
            <strong>{m.user}:</strong> {m.message}
          </p>
        ))}
      </div>

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Say hi..."
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
