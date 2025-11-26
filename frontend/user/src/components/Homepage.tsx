export default function Homepage() {
  const loginSpotify = () => {
    window.location.href = "http://localhost:8000/login";
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Welcome to Harmonify 🎧</h1>
      <button onClick={loginSpotify}>Login with Spotify</button>
    </div>
  );
}
