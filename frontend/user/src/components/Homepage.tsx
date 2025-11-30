export default function Homepage() {
  const loginSpotify = () => {
    window.location.href = "http://localhost:8000/login";
  };
  // simple homepage with login button that redirects to Spoify 2.0 OAuth flow
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Welcome to Harmonify</h1>
      <button onClick={loginSpotify}>Login with Spotify</button>
    </div>
  );
}
