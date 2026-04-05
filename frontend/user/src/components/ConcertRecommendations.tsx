import { useEffect, useState } from "react";
import "./style/ConcertRecommendations.css";
import { useNavigate } from "react-router-dom";

interface Concert {
  artist_name: string;
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
  const navigate = useNavigate();

  function getRoomId(concertUrl?: string) {
    if (!concertUrl) return null;

    const parts = concertUrl.split("/event/");
    return parts.length > 1 ? parts[1] : null;
  }

  useEffect(() => {
    const userId = localStorage.getItem("harmonify_user_id");

    if (!userId) {
      setError("User not authenticated");
      setLoading(false);
      return;
    }

    fetch(`http://localhost:8000/concerts-recommendations/?user_id=${userId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch concert recommendations");
        return res.json();
      })
      .then((data) => {
        const transformed = (data.concerts ?? []).map((c: any) => ({
          artist_name: c.artist,
          event_name: c.event_name,
          venue: c.venue,
          city: c.city,
          date: c.date,
          url: c.url,
        }));

        setConcerts(transformed);
        console.log("Fetched concerts:", transformed);
      })
      .catch((err) => {
        console.error(err);
        setError("Could not load concert recommendations");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <div className="top-bar" />
      <div className="content">
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
            {concerts.map((concert, index) => {
              const roomId = getRoomId(concert.url);

              return (
                <div key={index}>
                  <div className="card">
                    <div className="image-placeholder" />

                    <p className="text">
                      <strong>{concert.artist_name}</strong>
                      <br />
                      {concert.venue}, {concert.city}
                      <br />
                      {concert.date}
                    </p>

                    {concert.url ? (
                      <>
                        <a
                          href={concert.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <button className="chat-btn">
                            View Event
                          </button>
                        </a>

                        {roomId && (
                          <button
                            className="chat-btn"
                            onClick={() => navigate(`/concerts/${roomId}`)}
                          >
                            Join Chat 💬
                          </button>
                        )}
                      </>
                    ) : (
                      <p>No event URL available</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}