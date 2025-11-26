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

  useEffect(() => {
    if (!token) return;

    axios.get(`http://localhost:8000/profile?token=${token}`)
      .then(res => setProfile(res.data))
      .catch(console.error);

    axios.get(`http://localhost:8000/top-tracks?token=${token}`)
      .then(res => setTopTracks(res.data.items || []))
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
        {topTracks.map((track) => (
          <li key={track.id} style={{ marginBottom: "1rem" }}>
            <img
              src={track.album.images?.[2]?.url}
              alt="Album"
              width={50}
              style={{ borderRadius: 4, marginRight: 8 }}
            />
            <strong>{track.name}</strong>
            <span> — {track.artists.map((a: any) => a.name).join(", ")}</span>
          </li>
        ))}
      </ul>

      {/* Top Artists */}
      <h2>Your Top Artists 🎤</h2>
      <ul>
        {topArtists.map((artist) => (
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
