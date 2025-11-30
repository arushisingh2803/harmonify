import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";

export default function Dashboard() {
  const { search } = useLocation();
  const params = new URLSearchParams(search);
  const token = params.get("token");

  const [profile, setProfile] = useState<any>(null);
  const [topTracks, setTopTracks] = useState<any[]>([]);
  const [topArtists, setTopArtists] = useState<any[]>([]);

  async function fetchAudioFeatures(previewUrl: string) {
    if (!previewUrl) return null;

    try {
      const res = await axios.get(
        `http://localhost:8000/extract-features/?url=${encodeURIComponent(previewUrl)}`
      );
      return res.data;
    } catch (err) {
      console.error("Audio feature error:", err);
      return null;
    }
  }

  useEffect(() => {
    if (!token) return;

    axios.get(`http://localhost:8000/profile?token=${token}`)
      .then(res => setProfile(res.data))
      .catch(console.error);

    axios.get(`http://localhost:8000/top-tracks-with-snippets/?token=${token}`)
      .then(async (res) => {
        const tracks = res.data || [];

        const enrichedTracks = await Promise.all(
          tracks.map(async (t: any) => {
            const features = await fetchAudioFeatures(t.preview_url);
            return {
              ...t,
              audioFeatures: features
            };
          })
        );

        setTopTracks(enrichedTracks);
      })
      .catch(console.error);

    axios.get(`http://localhost:8000/top-artists?token=${token}`)
      .then(res => setTopArtists(res.data.items || []))
      .catch(console.error);
  }, [token]);

  if (!token) return <h2>No token found. Please login again.</h2>;
  if (!profile) return <h2>Loading your Spotify profile...</h2>;

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial" }}>
      <h1>Welcome, {profile.display_name} 👋</h1>

      {/* Profile section */}
      <img
        src={profile.images?.[0]?.url}
        alt="Profile"
        width={180}
        style={{ borderRadius: "50%", marginTop: "1rem" }}
      />
      <p>Email: {profile.email}</p>
      <p>Country: {profile.country}</p>
      <p>Followers: {profile.followers?.total}</p>
      <p>
        Spotify URL:{" "}
        <a href={profile.external_urls.spotify} target="_blank" rel="noreferrer">
          View Profile
        </a>
      </p>

      {/* Top Tracks */}
      <h2>Your Top Tracks 🎵</h2>
      <ul>
        {topTracks.map((t: any) => {
          const track = t.spotify_track;

          return (
            <li key={track.id} style={{ marginBottom: "2rem" }}>
              <img
                src={track.album.images?.[2]?.url}
                alt="Album"
                width={50}
                style={{ borderRadius: 4, marginRight: 8 }}
              />

              <strong>{track.name}</strong>
              <span> — {track.artists.map((a: any) => a.name).join(", ")}</span>

              {/* Audio Preview
              {t.preview_url && (
                <audio controls style={{ display: "block", marginTop: 8 }}>
                  <source src={t.preview_url} type="audio/mpeg" />
                </audio>
              )} */}

              {/* Audio Features */}
              {t.audioFeatures && (
                <div style={{ marginTop: "10px", paddingLeft: "12px" }}>
                  <p><strong>Tempo:</strong> {t.audioFeatures.tempo?.toFixed(2)} BPM</p>
                  <p><strong>Brightness (Centroid):</strong> {t.audioFeatures.centroid?.toFixed(2)}</p>
                  <p><strong>Noisiness (ZCR):</strong> {t.audioFeatures.zcr?.toFixed(4)}</p>
                </div>
              )}
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
              alt="Artist"
              width={50}
              style={{ borderRadius: 4, marginRight: 8 }}
            />
            <strong>{artist.name}</strong> — Popularity: {artist.popularity}
          </li>
        ))}
      </ul>
    </div>
  );
}
