import { useEffect, useState } from "react";
import "./style/ConcertRecommendations.css";

interface Concert {
  artist: string;
  event_name: string;
  venue: string;
  city: string;
  date: string;
  url?: string;
}

export default function ConcertRecommendations() {
  const [concerts, setConcerts] = useState<Concert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("spotify_token");

    if (!token) {
      setError("User not authenticated");
      setLoading(false);
      return;
    }

    fetch(
      `http://localhost:8000/concerts-recommendations/?token=${token}`
    )
      .then((res) => {
        if (!res.ok) {
          throw new Error("Failed to fetch concert recommendations");
        }
        return res.json();
      })
      .then((data) => {
        setConcerts(data.concerts ?? []);
      })
      .catch((err) => {
        console.error(err);
        setError("Could not load concert recommendations");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="page">
      {/* Top gradient bar */}
      <div className="top-bar" />

      <div className="content">

        {/* Main section */}
        <main className="main">
          <div className="header">
            <h1>Concert Recommendations for you</h1>
          </div>

          {loading && <p>Loading concerts… 🎶</p>}
          {error && <p className="error">{error}</p>}

          {!loading && !error && concerts.length === 0 && (
            <p>No upcoming concerts found for your top artists.</p>
          )}

          <div className="cards">
            {concerts.map((concert, index) => (
              <div className="card" key={index}>
                <div className="image-placeholder" />

                <p className="text">
                  <strong>{concert.artist}</strong>
                  <br />
                  {concert.venue}, {concert.city}
                  <br />
                  {concert.date}
                </p>

                {concert.url ? (
                  <a
                    href={concert.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <button className="chat-btn">View Event</button>
                  </a>
                ) : (
                  <button className="chat-btn">Join Chat</button>
                )}
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
