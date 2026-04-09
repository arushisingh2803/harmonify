import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

type AvgFeatures = {
  tempo: number;
  centroid: number;
  zcr: number;
  rms: number;
  energy: number;
  mood: number;
  mfcc: number[];
};

type PersonaData = {
  persona_type: string;
  persona_tags: string[];
  cluster_id: number;
};

const PERSONA_VISUALS: Record<string, {
  gradient: [string, string];
  accent: string;
  description: string;
}> = {
  "The Seeker":    { gradient: ["#6EE7B7", "#3B82F6"], accent: "#3B82F6", description: "You roam across genres, always chasing something new." },
  "The Guardian":  { gradient: ["#6366f1", "#8b5cf6"], accent: "#6366f1", description: "You protect what matters — your taste is your identity." },
  "The Zealous":   { gradient: ["#f97316", "#ef4444"], accent: "#f97316", description: "High tempo, high intensity — music as fuel." },
  "The Wistful":   { gradient: ["#fb923c", "#fbbf24"], accent: "#fb923c", description: "You find comfort in sounds that carry memory." },
  "The Formalist": { gradient: ["#14b8a6", "#0ea5e9"], accent: "#14b8a6", description: "One genre. Total mastery. No compromises." },
};

const DEFAULT_VISUAL = {
  gradient: ["#c8c8c8", "#a0a0a0"] as [string, string],
  accent: "#888",
  description: "Listen to more music to reveal your persona!",
};

function getEnergyStatement(energy: number): string {
  if (energy > 75) return "High Energy. Your music is kinetic and bold.";
  if (energy > 50) return "Moderate Energy. Your music is yin and yang - balanced.";
  if (energy > 25) return "Low Energy. Your music is introspective and gentle.";
  return "Minimal Energy. Your music is ambient and atmospheric.";
}

function getMoodStatement(mood: number): string {
  if (mood > 75) return "Bright Mood. Your music is uplifting and vibrant.";
  if (mood > 50) return "Balanced Mood. Your music has a mix of light and dark tones.";
  if (mood > 25) return "Subtle Mood. Your music leans towards melancholy.";
  return "Dark Mood. Your music is brooding and atmospheric.";
}

// pulse ring for the energy visual
function PulseRing({ energy, accent }: { energy: number; accent: string }) {
  const size     = 110;
  const cx       = size / 2;
  const cy       = size / 2;
  const minR     = 12;
  const maxR     = 44;
  const radius   = minR + (energy / 100) * (maxR - minR);
  const duration = 2.2 - (energy / 100) * 1.4;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
        <style>{`
          @keyframes pr1 { 0% { r: ${radius * 0.35}px; opacity: 0.9; } 100% { r: ${radius}px; opacity: 0; } }
          @keyframes pr2 { 0% { r: ${radius * 0.35}px; opacity: 0.6; } 100% { r: ${radius}px; opacity: 0; } }
          @keyframes pr3 { 0% { r: ${radius * 0.35}px; opacity: 0.3; } 100% { r: ${radius}px; opacity: 0; } }
          @keyframes prc { 0%,100% { r: ${minR * 0.65}px; } 50% { r: ${minR}px; } }
          .pr1 { animation: pr1 ${duration}s ease-out infinite; }
          .pr2 { animation: pr2 ${duration}s ease-out infinite ${(duration * 0.33).toFixed(2)}s; }
          .pr3 { animation: pr3 ${duration}s ease-out infinite ${(duration * 0.66).toFixed(2)}s; }
          .prc { animation: prc ${duration}s ease-in-out infinite; }
        `}</style>
        <circle className="pr1" cx={cx} cy={cy} r={radius * 0.35} fill="none" stroke={accent} strokeWidth="1.5"/>
        <circle className="pr2" cx={cx} cy={cy} r={radius * 0.35} fill="none" stroke={accent} strokeWidth="1"/>
        <circle className="pr3" cx={cx} cy={cy} r={radius * 0.35} fill="none" stroke={accent} strokeWidth="0.5"/>
        <circle className="prc" cx={cx} cy={cy} r={minR * 0.65}
          fill={accent} fillOpacity="0.12" stroke={accent} strokeWidth="2"/>
        <circle cx={cx} cy={cy} r="4" fill={accent}/>
      </svg>

      <div style={{ flex: 1 }}>
        <p style={{
          margin: "0 0 4px",
          fontSize: "2rem", fontWeight: 800, lineHeight: 1,
          color: accent, fontFamily: "'Lato', sans-serif",
        }}>
          {energy.toFixed(0)}<span style={{ fontSize: "1rem", fontWeight: 600 }}>%</span>
        </p>
        <p style={{
          margin: 0, fontSize: "0.75rem", color: "#777",
          fontStyle: "italic", lineHeight: 1.6,
          fontFamily: "'Lato', sans-serif",
          borderLeft: `3px solid ${accent}50`,
          paddingLeft: "0.65rem",
        }}>
          {getEnergyStatement(energy)}
        </p>
      </div>
    </div>
  );
}

// bar waveform for the mood visual
function WaveformBar({ value, accent, seed }: { value: number; accent: string; seed: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef  = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const BAR_COUNT = 36;
    const W = canvas.width;
    const H = canvas.height;
    const barW = W / BAR_COUNT;
    const gap  = 3;

    const heights = Array.from({ length: BAR_COUNT }, (_, i) => {
      const norm   = value / 100;
      const base   = norm * Math.abs(Math.sin(i * 0.6 + seed));
      const detail = 0.2 * Math.abs(Math.sin(i * 1.8 + seed * 2));
      return Math.max(0.06, base + detail);
    });

    function draw(ts: number) {
      ctx!.clearRect(0, 0, W, H);
      for (let i = 0; i < BAR_COUNT; i++) {
        const wave   = Math.sin(ts * 0.0018 + i * 0.45 + seed) * 0.12;
        const height = Math.max(4, (heights[i] + wave) * H * 0.88);
        const x      = i * barW + gap / 2;
        const y      = (H - height) / 2;
        const r      = Math.min((barW - gap) / 2, 3);
        const opacity = 0.3 + heights[i] * 0.7;

        ctx!.fillStyle = accent + Math.round(Math.min(opacity, 1) * 255).toString(16).padStart(2, "0");

        ctx!.beginPath();
        ctx!.moveTo(x + r, y);
        ctx!.lineTo(x + barW - gap - r, y);
        ctx!.quadraticCurveTo(x + barW - gap, y, x + barW - gap, y + r);
        ctx!.lineTo(x + barW - gap, y + height - r);
        ctx!.quadraticCurveTo(x + barW - gap, y + height, x + barW - gap - r, y + height);
        ctx!.lineTo(x + r, y + height);
        ctx!.quadraticCurveTo(x, y + height, x, y + height - r);
        ctx!.lineTo(x, y + r);
        ctx!.quadraticCurveTo(x, y, x + r, y);
        ctx!.closePath();
        ctx!.fill();
      }
      frameRef.current = requestAnimationFrame(draw);
    }

    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [value, accent, seed]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={80}
      style={{ width: "100%", height: "80px", borderRadius: "8px" }}
    />
  );
}

// persona shape svg components - animated based on persona type
function PersonaShape({ personaType, accent }: { personaType: string; accent: string }): React.ReactElement {
  const shapes: Record<string, React.ReactElement> = {
    "The Seeker": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`
          @keyframes exp-spin { to { transform: rotate(360deg); } }
          @keyframes exp-pulse { 0%,100%{r:8px} 50%{r:12px} }
          .exp-g { transform-origin: 50px 50px; animation: exp-spin 14s linear infinite; }
          .exp-c { animation: exp-pulse 2s ease-in-out infinite; }
        `}</style>
        <g className="exp-g">
          {[0,30,60,90,120,150,180,210,240,270,300,330].map((deg, i) => (
            <line key={i} x1="50" y1="50"
              x2={50 + 42 * Math.cos(deg * Math.PI / 180)}
              y2={50 + 42 * Math.sin(deg * Math.PI / 180)}
              stroke={accent} strokeWidth={i % 3 === 0 ? 2 : 1}
              strokeOpacity={i % 2 === 0 ? 0.9 : 0.35}
            />
          ))}
        </g>
        <circle className="exp-c" cx="50" cy="50" r="8" fill={accent} fillOpacity="0.9"/>
      </svg>
    ),
    "The Guardian": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`
          @keyframes grd-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.94)} }
          .grd-s { transform-origin:50px 50px; animation: grd-pulse 2.5s ease-in-out infinite; }
        `}</style>
        <polygon className="grd-s" points="50,10 90,30 90,65 50,90 10,65 10,30"
          fill="none" stroke={accent} strokeWidth="2" strokeOpacity="0.9"/>
        <polygon className="grd-s" points="50,22 78,37 78,62 50,78 22,62 22,37"
          fill="none" stroke={accent} strokeWidth="1.5" strokeOpacity="0.5"
          style={{ animationDelay: "0.3s" }}/>
        <circle cx="50" cy="50" r="6" fill={accent}/>
      </svg>
    ),
    "The Zealous": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes bolt-flash { 0%,100%{opacity:1} 50%{opacity:0.4} } .bolt { animation: bolt-flash 1.2s ease-in-out infinite; }`}</style>
        <polygon className="bolt" points="58,12 36,54 52,54 42,88 68,46 52,46" fill={accent} fillOpacity="0.9"/>
      </svg>
    ),
    "The Wistful": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes nos-breathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.08)} } .nos-e { transform-origin:50px 50px; animation: nos-breathe 3.5s ease-in-out infinite; }`}</style>
        {[44,32,20,9].map((ry, i) => (
          <ellipse key={i} className="nos-e" cx="50" cy="50"
            rx={ry * 1.4} ry={ry} fill="none" stroke={accent}
            strokeWidth="1.5" strokeOpacity={1 - i * 0.2}
            style={{ animationDelay: `${i * 0.3}s` }}/>
        ))}
        <ellipse cx="50" cy="50" rx="6" ry="4" fill={accent}/>
      </svg>
    ),
    "The Formalist": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes pur-fill { 0%,100%{opacity:0.25} 50%{opacity:1} } .pur-c { animation: pur-fill 2.4s ease-in-out infinite; }`}</style>
        {[0,1,2,3,4].map(row => [0,1,2,3,4].map(col => (
          <rect key={`${row}-${col}`} className="pur-c"
            x={15 + col * 15} y={15 + row * 15} width="11" height="11" rx="2"
            fill={accent} style={{ animationDelay: `${(row + col) * 0.08}s` }}/>
        )))}
      </svg>
    ),
  };

  return shapes[personaType] ?? (
    <svg viewBox="0 0 100 100" width="90" height="90">
      <circle cx="50" cy="50" r="38" fill="none" stroke="#ccc" strokeWidth="2"/>
    </svg>
  );
}

// main component
export default function AudioProfileChart({
  avg,
  userId,
}: {
  avg: AvgFeatures;
  userId?: string;
}) {
  const [persona, setPersona] = useState<PersonaData | null>(null);

  useEffect(() => {
    if (!userId) return;
    axios
      .get(`http://localhost:8000/user-persona/?user_id=${userId}`)
      .then(res => setPersona(res.data))
      .catch(() => setPersona(null));
  }, [userId]);

  if (!avg) return null;

  const visual = persona
    ? (PERSONA_VISUALS[persona.persona_type] ?? DEFAULT_VISUAL)
    : DEFAULT_VISUAL;

  const energy = Math.min((avg.energy / 0.30) * 100, 100);
  const mood   = Math.min(((avg.mood - 500) / 7500) * 100, 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

      {/* Persona card */}
      {persona ? (
        <div style={{
          display: "flex", alignItems: "center", gap: "1.25rem",
          padding: "1.25rem", borderRadius: "16px",
          background: `linear-gradient(135deg, ${visual.gradient[0]}18, ${visual.gradient[1]}10)`,
          border: `1.5px solid ${visual.accent}30`,
        }}>
          <PersonaShape personaType={persona.persona_type} accent={visual.accent}/>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{
              margin: "0 0 2px", fontSize: "0.65rem", fontWeight: 700,
              letterSpacing: "0.1em", textTransform: "uppercase",
              color: visual.accent, fontFamily: "'Lato', sans-serif",
            }}>
              Your Music Persona
            </p>
            <h3 style={{
              margin: "0 0 4px", fontSize: "1.3rem", fontWeight: 800,
              color: "#1a1a2e", fontFamily: "'Lato', sans-serif", lineHeight: 1.15,
            }}>
              {persona.persona_type}
            </h3>
            <p style={{
              margin: "0 0 10px", fontSize: "0.78rem", color: "#777",
              fontStyle: "italic", fontFamily: "'Lato', sans-serif",
            }}>
              {visual.description}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {persona.persona_tags.map((tag, i) => (
                <span key={i} style={{
                  padding: "0.2rem 0.7rem", borderRadius: "999px",
                  fontSize: "0.7rem", fontWeight: 700,
                  fontFamily: "'Lato', sans-serif",
                  background: `${visual.accent}18`, color: visual.accent,
                  border: `1px solid ${visual.accent}40`,
                  letterSpacing: "0.03em",
                }}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div style={{
          padding: "1rem 1.25rem", borderRadius: "16px",
          background: "#f0f0f0", color: "#aaa",
          fontSize: "0.8rem", fontFamily: "'Lato', sans-serif", textAlign: "center",
        }}>
          Persona not yet assigned — listen to more music to reveal your unique profile!
        </div>
      )}

      <div style={{ borderTop: "1px solid #f0f0f0" }}/>

      {/* Energy — pulse ring */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <p style={{
          margin: 0, fontSize: "0.62rem", fontWeight: 700,
          letterSpacing: "0.1em", textTransform: "uppercase",
          color: "#aaa", fontFamily: "'Lato', sans-serif",
        }}>
          Energy
        </p>
        <PulseRing energy={energy} accent={visual.accent}/>
      </div>

      <div style={{ borderTop: "1px solid #f0f0f0" }}/>

      {/* Mood — bar waveform */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <p style={{
            margin: 0, fontSize: "0.62rem", fontWeight: 700,
            letterSpacing: "0.1em", textTransform: "uppercase",
            color: "#aaa", fontFamily: "'Lato', sans-serif",
          }}>
            Mood
          </p>
          <p style={{
            margin: 0, fontSize: "1rem", fontWeight: 800,
            color: visual.accent, fontFamily: "'Lato', sans-serif",
          }}>
            {mood.toFixed(0)}%
          </p>
        </div>
        <WaveformBar value={mood} accent={visual.accent} seed={3.7}/>
        <p style={{
          margin: 0, fontSize: "0.75rem", color: "#777",
          fontStyle: "italic", lineHeight: 1.6,
          fontFamily: "'Lato', sans-serif",
          borderLeft: `3px solid ${visual.accent}50`,
          paddingLeft: "0.65rem",
        }}>
          {getMoodStatement(mood)}
        </p>
      </div>

    </div>
  );
}