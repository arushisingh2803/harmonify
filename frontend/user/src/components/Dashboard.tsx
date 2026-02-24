import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import AudioProfileChart from "./AudioProfileChart.tsx";

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

  async function fetchAudioFeatures(previewUrl: string) {
    if (!previewUrl) return null;

    try {
      const res = await axios.get(
        `http://localhost:8000/extract-features/?url=${encodeURIComponent(
          previewUrl
        )}`
      );
      return res.data;
    } catch (err) {
      console.error("Audio feature error:", err);
      return null;
    }
  }
  
  // storing token in localStorage. 
  useEffect(() => {
    if (token) {
      localStorage.setItem("spotify_token", token);
    }
  }, [token]);

  //storing spotify username in localStorage for the concert chat feature
  useEffect(() => {
    if (profile?.display_name) {
      localStorage.setItem("spotify_username", profile.display_name);
    }
  }, [profile]);

  // axios is used for calls to the backend in order to fetch user data and render it to frontend
  useEffect(() => {
    if (!token) return;
    
    setLoading(true);

    axios
      .get(`http://localhost:8000/profile?token=${token}`)
      .then((res) => setProfile(res.data))
      .catch(console.error);

    axios
      .get(`http://localhost:8000/top-tracks-with-snippets/?token=${token}&time_range=${timeRange}`)
      .then(async (res) => {
        const data = res.data;

        if (data.tracks) {
          const enriched = await Promise.all(
            data.tracks.map(async (t: any) => {
              const features = await fetchAudioFeatures(t.preview_url);
              return {
                ...t,
                audioFeatures: features,
              };
            })
          );

          setTopTracks(enriched);
        }

        if (data.average_features) {
          setAvgFeatures(data.average_features);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    axios
      .get(`http://localhost:8000/top-artists?token=${token}&time_range=${timeRange}`)
      .then((res) => setTopArtists(res.data.items || []))
      .catch(console.error);
  }, [token, timeRange]);

  if (!token) return <h2>No token found. Please login again.</h2>;
  if (!profile) return <h2>Loading your Spotify profile...</h2>;

return (
  <div style={{ margin: "50px", padding: "2rem", fontFamily: "Arial" }}> {/* styling is limited to this at the moment */}
    <h1>Welcome, {profile.display_name} 👋</h1>

    <div
      style={{
        display: "flex",
        gap: "3rem",
        alignItems: "flex-start",
      }}
    >
      <div style={{ flex: 1 }}>

        {/* Profile section */}
        <img
          src={profile.images?.[0]?.url}
          alt="Profile"
          width={150}
          style={{ borderRadius: "50%", marginTop: "1rem" }}
        />
        <p>Email: {profile.email}</p>
        <p>Country: {profile.country}</p>
        <p>Followers: {profile.followers?.total}</p>
        <p>
          Spotify URL:{" "}
          <a
            href={profile.external_urls.spotify}
            target="_blank"
            rel="noreferrer"
          >
            View Profile
          </a>
        </p>
      <div style={{ marginBottom: "1rem" }}>
        <strong>Time Range:</strong>{" "}
        <button onClick={() => setTimeRange("short_term")}>
          Last 4 Weeks
        </button>

        <button onClick={() => setTimeRange("medium_term")}>
          Last 6 Months
        </button>

        <button onClick={() => setTimeRange("long_term")}>
          All Time
        </button>
      </div>
      {loading ? (
        <p>Loading your music data… </p>
      ) : (
        <>
          {/* Top Tracks */}
          <h2>Your Top Tracks 🎵</h2>
          <ul>
            {topTracks.map((t: any) => {
              const track = t.spotify_track;
              return (
                <li key={track.id} style={{ marginBottom: "1.5rem" }}>
                  <img
                    src={track.album.images?.[2]?.url}
                    alt="Album"
                    width={50}
                    style={{
                      borderRadius: 4,
                      marginRight: 8,
                      verticalAlign: "middle",
                    }}
                  />
                  <strong>{track.name}</strong>
                  <span>
                    {" "}
                    — {track.artists.map((a: any) => a.name).join(", ")}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Top Artists */}
          <h2>Your Top Artists 🎤</h2>
          <ul>
            {topArtists.map((artist: any) => (
              <li key={artist.id} style={{ marginBottom: "1rem" }}>
                <img
                  src={artist.images?.[2]?.url}
                  width={50}
                  alt="Artist"
                  style={{
                    borderRadius: 4,
                    marginRight: 8,
                    verticalAlign: "middle",
                  }}
                />
                <strong>{artist.name}</strong> — Popularity: {artist.popularity}
              </li>
            ))}
          </ul>
        </>
      )}

      </div>

      {/* Audio Profile Chart */}
      <div style={{ flex: 1, maxWidth: "600px" }}>
        {avgFeatures && <AudioProfileChart avg={avgFeatures} />}
      </div>
    </div>
  </div>
  
);

}
