import "./style/ConcertRecommendations.css";

export default function ConcertRecommendations() {
  const concerts = [
    {
      artist: "Artist Name",
      venue: "Venue",
      date: "12 Mar 2026",
    },
    {
      artist: "Artist Name",
      venue: "Venue",
      date: "18 Mar 2026",
    },
    {
      artist: "Artist Name",
      venue: "Venue",
      date: "25 Mar 2026",
    },
    {
      artist: "Artist Name",
      venue: "Venue",
      date: "02 Apr 2026",
    },
  ];

  return (
    <div className="page">
      {/* Top gradient bar */}
      <div className="top-bar" />

      <div className="content">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="icon">🏆</div>
          <div className="icon">👥</div>
          <div className="icon">💬</div>
        </aside>

        {/* Main section */}
        <main className="main">
          <div className="header">
            <h1>Concert Recommendations for @user</h1>
            <button className="filter-btn">☰ Filter by Location</button>
          </div>

          <div className="cards">
            {concerts.map((concert, index) => (
              <div className="card" key={index}>
                <div className="image-placeholder" />
                <p className="text">
                  <strong>{concert.artist}</strong>
                  <br />
                  {concert.venue}
                  <br />
                  {concert.date}
                </p>
                <button className="chat-btn">Join Chat</button>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
