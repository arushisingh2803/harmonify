import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { FaHome, FaMusic, FaUsers } from "react-icons/fa";
import "./style/Dashboard.css";
import AudioProfileChart from "./AudioProfileChart.tsx";
import ConcertRecommendations from "./ConcertRecommendations.tsx";
import SimilarUsers from "./SimilarUsers.tsx"

export default function Dashboard() {
  const { search } = useLocation();
  const params = new URLSearchParams(search);
  const userId = params.get("user_id");

  const [profile, setProfile]       = useState<any>(null);
  const [topTracks, setTopTracks]   = useState<any[]>([]);
  const [topArtists, setTopArtists] = useState<any[]>([]);
  const [avgFeatures, setAvgFeatures] = useState<any>(null);
  const [loading, setLoading]       = useState(false);
  const [timeRange, setTimeRange]   = useState<"short_term" | "medium_term" | "long_term">("long_term");
  const [activeTab, setActiveTab]   = useState<"dashboard" | "concerts" | "matches">("dashboard");
  const [musicView, setMusicView]   = useState<"tracks" | "artists">("tracks");

  useEffect(() => {
    if (userId) localStorage.setItem("harmonify_user_id", userId);
  }, [userId]);

  useEffect(() => {
    if (profile?.display_name) {
      localStorage.setItem("spotify_username", profile.display_name);
    }
  }, [profile]);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);

    axios.get(`http://localhost:8000/profile/?user_id=${userId}`)
      .then(res => setProfile(res.data))
      .catch(console.error);

    axios.get(`http://localhost:8000/top-tracks-with-snippets/?user_id=${userId}&time_range=${timeRange}`)
      .then(res => {
        const data = res.data;
        if (data.tracks)          setTopTracks(data.tracks.slice(0, 10));
        if (data.average_features) setAvgFeatures(data.average_features);
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    axios.get(`http://localhost:8000/top-artists/?user_id=${userId}&time_range=${timeRange}`)
      .then(res => setTopArtists((res.data.items || []).slice(0, 10)))
      .catch(console.error);

  }, [userId, timeRange]);

  if (!userId)  return <h2>No session found. Please <a href="http://localhost:8000/login/">login again</a>.</h2>;
  if (!profile) return <h2>Loading your Spotify profile...</h2>;

  const timeRangeLabels = {
    short_term:  "Last 4 Weeks",
    medium_term: "Last 6 Months",
    long_term:   "All Time",
  };

  return (
    <div className="dashboard-page">

      {/* Sidebar */}
      <div className="sidebar">
        <button className={activeTab === "dashboard" ? "active" : ""} onClick={() => setActiveTab("dashboard")}>
          <FaHome size={24} />
        </button>
        <button className={activeTab === "concerts" ? "active" : ""} onClick={() => setActiveTab("concerts")}>
          <FaMusic size={24} />
        </button>
        <button className={activeTab === "matches" ? "active" : ""} onClick={() => setActiveTab("matches")}>
          <FaUsers size={24} />
        </button>
      </div>

      {/* Main content */}
      <div className="dashboard-content">
      {activeTab === "dashboard" && (
        <div className="main-layout">

          {/* Left Column */}
          <div className="left-column">

            {/* Profile */}
            <div className="card profile-card">
              <img src={profile.images?.[0]?.url} alt="Profile" />
              <div>
                <h3>{profile.display_name}</h3>
                <small style={{ color: "#999", fontSize: "0.75rem" }}>Spotify Profile</small>
              </div>
            </div>

            {/* Music card */}
            {loading ? (
              <div className="card" style={{ alignItems: "center", justifyContent: "center", padding: "2rem" }}>
                <p style={{ color: "#aaa", margin: 0 }}>Loading your music data…</p>
              </div>
            ) : (
              <div className="card music-card">

                {/* Time range */}
                <div className="time-range">
                  <strong>Time Range:</strong>
                  {(["short_term", "medium_term", "long_term"] as const).map(range => (
                    <button
                      key={range}
                      className={timeRange === range ? "active" : ""}
                      onClick={() => setTimeRange(range)}
                    >
                      {timeRangeLabels[range]}
                    </button>
                  ))}
                </div>

                {/* Toggle */}
                <div className="music-toggle">
                  <button
                    className={musicView === "tracks" ? "active" : ""}
                    onClick={() => setMusicView("tracks")}
                  >
                    Top Tracks
                  </button>
                  <button
                    className={musicView === "artists" ? "active" : ""}
                    onClick={() => setMusicView("artists")}
                  >
                    Top Artists
                  </button>
                </div>

                {/* Tracks */}
                {musicView === "tracks" && (
                  <ul className="music-list">
                    {topTracks.map((t: any, idx: number) => {
                      const track = t.spotify_track;
                      return (
                        <li key={track.id}>
                          <span className="music-rank">{idx + 1}</span>
                          <img src={track.album.images?.[2]?.url} alt={track.name} />
                          <div>
                            <strong>{track.name}</strong>
                            <small>{track.artists.map((a: any) => a.name).join(", ")}</small>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}

                {/* Artists */}
                {musicView === "artists" && (
                  <ul className="music-list">
                    {topArtists.map((a: any, idx: number) => (
                      <li key={a.id}>
                        <span className="music-rank">{idx + 1}</span>
                        <img
                          src={a.images?.[2]?.url}
                          alt={a.name}
                          className="artist-img"
                        />
                        <div>
                          <strong>{a.name}</strong>
                          <small>
                            {`Popularity: ${a.popularity}`}
                          </small>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

              </div>
            )}
          </div>

          {/* Right Column */}
          {avgFeatures && (
            <div className="right-column card chart-card">
              <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem", fontWeight: 700, color: "#1a1a2e" }}>
                Your Audio Profile
              </h4>
              <AudioProfileChart avg={avgFeatures} userId={userId ?? undefined} />
            </div>
          )}

        </div>
      )}

        {activeTab === "concerts" && (
          <div className="card">
            <ConcertRecommendations />
          </div>
        )}
      </div>

      {activeTab === "matches" && (
        <SimilarUsers userId={userId ?? ""} />
      )}

    </div>
  );
}