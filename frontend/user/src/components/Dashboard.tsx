import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import AudioProfileChart from "./AudioProfileChart.tsx";
import { FaHome, FaMusic } from "react-icons/fa";
import "./style/Dashboard.css";

export default function Dashboard() {
  const { search } = useLocation();
  const params = new URLSearchParams(search);
  const token = params.get("token");

  const [profile, setProfile] = useState<any>(null);
  const [topTracks, setTopTracks] = useState<any[]>([]);
  const [topArtists, setTopArtists] = useState<any[]>([]);
  const [avgFeatures, setAvgFeatures] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState<"short_term" | "medium_term" | "long_term">("long_term");
  const [activeTab, setActiveTab] = useState<"dashboard" | "concerts">("dashboard");

  async function fetchAudioFeatures(previewUrl: string) {
    if (!previewUrl) return null;
    try {
      const res = await axios.get(`http://localhost:8000/extract-features/?url=${encodeURIComponent(previewUrl)}`);
      return res.data;
    } catch {
      return null;
    }
  }

  useEffect(() => { if (token) localStorage.setItem("spotify_token", token); }, [token]);
  useEffect(() => { if (profile?.display_name) localStorage.setItem("spotify_username", profile.display_name); }, [profile]);

  useEffect(() => {
    if (!token) return;

    setLoading(true);

    axios.get(`http://localhost:8000/profile?token=${token}`).then(res => setProfile(res.data)).catch(console.error);

    axios.get(`http://localhost:8000/top-tracks-with-snippets/?token=${token}&time_range=${timeRange}`)
      .then(async (res) => {
        const data = res.data;
        if (data.tracks) {
          const enriched = await Promise.all(
            data.tracks.map(async (t: any) => ({ ...t, audioFeatures: await fetchAudioFeatures(t.preview_url) }))
          );
          setTopTracks(enriched);
        }
        if (data.average_features) setAvgFeatures(data.average_features);
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    axios.get(`http://localhost:8000/top-artists?token=${token}&time_range=${timeRange}`)
      .then(res => setTopArtists(res.data.items || []))
      .catch(console.error);
  }, [token, timeRange]);

  if (!token) return <h2>No token found. Please login again.</h2>;
  if (!profile) return <h2>Loading your Spotify profile...</h2>;

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
      </div>

      {/* Main content */}
      <div className="dashboard-content">
        {activeTab === "dashboard" && (
          <div className="main-layout">
            {/* Left Column: Profile + Tracks + Artists */}
            <div className="left-column">
              <div className="card profile-card">
                <img src={profile.images?.[0]?.url} alt="Profile" width={80} />
                <h3>{profile.display_name}</h3>
              </div>

              {loading ? <p>Loading your music data…</p> : (
                <>
                  <div className="card">
                    <div className="time-range">
                      <strong>Time Range:</strong>{" "}
                      <button onClick={() => setTimeRange("short_term")}>
                        Last 4 Weeks
                      </button>
                      <button onClick={() => setTimeRange("medium_term")} >
                        Last 6 Months
                      </button>
                      <button onClick={() => setTimeRange("long_term")}>
                        All Time
                      </button>
                    </div>
                    <h4>Your Top Tracks 🎵</h4>
                    <ul className="music-list">
                      {topTracks.map((t: any) => {
                        const track = t.spotify_track;
                        return (
                          <li key={track.id}>
                            <img src={track.album.images?.[2]?.url} width={50} />
                            <div>
                              <strong>{track.name}</strong><br/>
                              <small>{track.artists.map((a: any) => a.name).join(", ")}</small>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>

                  <div className="card">
                    <h4>Your Top Artists 🎤</h4>
                    <ul className="music-list">
                      {topArtists.map((a: any) => (
                        <li key={a.id}>
                          <img src={a.images?.[2]?.url} width={50} />
                          <div>
                            <strong>{a.name}</strong><br/>
                            <small>Popularity: {a.popularity}</small>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>

            {/* Right Column: Audio Analysis */}
            {avgFeatures && (
              <div className="right-column card chart-card">
                <h4>Your Audio Profile</h4>
                <AudioProfileChart avg={avgFeatures} />
              </div>
            )}
          </div>
        )}

        {activeTab === "concerts" && (
          <div className="card">
            <h4>Concert Chat (coming soon)</h4>
          </div>
        )}
      </div>

    </div>
  );
}