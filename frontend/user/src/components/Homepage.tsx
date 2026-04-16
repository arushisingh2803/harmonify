import "./style/Homepage.css";
import { useEffect, useRef } from "react";

export default function Homepage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  const loginSpotify = () => {
    window.location.href = "http://localhost:8000/login";
  };

  // Animated waveform on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = 220;
    };
    resize();
    window.addEventListener("resize", resize);

    let t = 0;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const midY = h / 2;

      const waves = [
        { amp: 55, freq: 0.008, speed: 0.01, color: "rgba(80,80,80,1)",   lineWidth: 2.5 },
        { amp: 35, freq: 0.013, speed: 0.05, color: "rgba(80,80,80,0.5)", lineWidth: 1.5 },
        { amp: 20, freq: 0.022, speed: 0.09, color: "rgba(80,80,80,0.3)", lineWidth: 1   },
      ];

      waves.forEach(({ amp, freq, speed, color, lineWidth }) => {
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";

        for (let x = 0; x <= w; x += 2) {
          const y =
            midY +
            amp * Math.sin(freq * x + t * speed * 60) +
            (amp * 0.4) * Math.sin(freq * 1.7 * x + t * speed * 40 + 1.2);

          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }

        ctx.stroke();
      });

      t += 1;
      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  useEffect(() => {
    const items = document.querySelectorAll(".feature-item");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("visible");
        });
      },
      { threshold: 0.1 }
    );
    items.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="homepage">

      {/* Aura blobs */}
      <div className="aura one"></div>
      <div className="aura two"></div>
      <div className="aura three"></div>
      <div className="aura four"></div>
      <div className="aura five"></div>
      <div className="aura six"></div>

      {/* Animated waveform behind content */}
      <canvas ref={canvasRef} className="waveform-canvas" />

      {/* Hero */}
      <section className="hero">
        <h1 className="hero-title">harmonify.</h1>
        <p className="hero-subtitle">your music personified.</p>
        <button className="spotify-button" onClick={loginSpotify}>
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/8/84/Spotify_icon.svg"
            alt="Spotify logo"
            className="spotify-icon"
          />
          Login with Spotify
        </button>
      </section>

      {/* Features */}
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

      <footer className="footer">
        <p>© 2026 Harmonify</p>
      </footer>

    </div>
  );
}