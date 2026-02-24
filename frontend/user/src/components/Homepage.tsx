import "./style/Homepage.css";
import { useEffect } from "react";

export default function Homepage() {
  const loginSpotify = () => {
    window.location.href = "http://localhost:8000/login";
  };

    useEffect(() => {
    const items = document.querySelectorAll(".feature-item");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.2 }
    );

    items.forEach((item) => observer.observe(item));
  }, []);

  return (
    <div className="homepage">

        <div className="aura one"></div>
        <div className="aura two"></div>
        <div className="aura three"></div>
        <div className="aura four"></div>
        <div className="aura five"></div>
        <div className="aura six"></div>

      <section className="hero">
        <h1 className="hero-title">harmonify.</h1>
        <p className="hero-subtitle">
          your music personified.
        </p>
        <button className="spotify-button" onClick={loginSpotify}>
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/8/84/Spotify_icon.svg"
            alt="Spotify logo"
            className="spotify-icon"
          />
          Login with Spotify
        </button>
      </section>

      <section className="features">
        <div className="feature-item">
          <h2>your music persona</h2>
          <p>decode the patterns behind your listening habits</p>
        </div>
        <div className="feature-item">
          <h2>your sonic circle</h2>
          <p>meet people who share your music taste.</p>
        </div>
        <div className="feature-item">
          <h2>live your sound</h2>
          <p>discover shows that match your favourite genres.</p>
        </div>
      </section>
      <section className="features">

    </section>

      <footer className="footer">
        <p>© 2026 Harmonify</p>
      </footer>
    </div>
  );
}