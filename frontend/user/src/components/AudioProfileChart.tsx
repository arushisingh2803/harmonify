import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { useEffect, useState } from "react";
import axios from "axios";

ChartJS.register(ArcElement, Tooltip, Legend);

type AvgFeatures = {
  tempo: number;
  centroid: number;
  zcr: number;
  rms: number;
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
  "The Socialite": { gradient: ["#ec4899", "#f43f5e"], accent: "#ec4899", description: "You're tuned into the pulse of what's popular." },
  "The Formalist": { gradient: ["#14b8a6", "#0ea5e9"], accent: "#14b8a6", description: "One genre. Total mastery. No compromises." },
};

const DEFAULT_VISUAL = {
  gradient: ["#c8c8c8", "#a0a0a0"] as [string, string],
  accent: "#888",
  description: "Your musical identity is taking shape.",
};

function PersonaShape({ personaType, accent }: { personaType: string; accent: string }) {
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
          @keyframes cur-breathe { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.9)} }
          .cur-r { transform-origin: 50px 50px; animation: cur-breathe 3s ease-in-out infinite; }
        `}</style>
        {[42,30,18,8].map((r, i) => (
          <circle key={i} className="cur-r" cx="50" cy="50" r={r}
            fill="none" stroke={accent} strokeWidth="1.5"
            strokeOpacity={1 - i * 0.2}
            style={{ animationDelay: `${i * 0.25}s` }}
          />
        ))}
        <circle cx="50" cy="50" r="4" fill={accent}/>
      </svg>
    ),
    "The Zealous": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes bolt-flash { 0%,100%{opacity:1} 50%{opacity:0.4} } .bolt { animation: bolt-flash 1.2s ease-in-out infinite; }`}</style>
        <polygon className="bolt"
          points="58,12 36,54 52,54 42,88 68,46 52,46"
          fill={accent} fillOpacity="0.9"
        />
      </svg>
    ),
    "The Wistful": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes nos-breathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.08)} } .nos-e { transform-origin:50px 50px; animation: nos-breathe 3.5s ease-in-out infinite; }`}</style>
        {[44,32,20,9].map((ry, i) => (
          <ellipse key={i} className="nos-e" cx="50" cy="50"
            rx={ry * 1.4} ry={ry}
            fill="none" stroke={accent} strokeWidth="1.5"
            strokeOpacity={1 - i * 0.2}
            style={{ animationDelay: `${i * 0.3}s` }}
          />
        ))}
        <ellipse cx="50" cy="50" rx="6" ry="4" fill={accent}/>
      </svg>
    ),
    "The Socialite": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes soc-pop { 0%,100%{opacity:1} 50%{opacity:0.5} } .soc-n { animation: soc-pop 2s ease-in-out infinite; }`}</style>
        {([[50,50],[22,30],[78,30],[15,68],[85,68],[50,88]] as [number,number][]).map(([x,y], i) => (
          <g key={i}>
            {i > 0 && <line x1="50" y1="50" x2={x} y2={y} stroke={accent} strokeWidth="1" strokeOpacity="0.4"/>}
            <circle className="soc-n" cx={x} cy={y} r={i === 0 ? 9 : 5}
              fill={accent} fillOpacity={i === 0 ? 1 : 0.65}
              style={{ animationDelay: `${i * 0.18}s` }}
            />
          </g>
        ))}
      </svg>
    ),
    "The Formalist": (
      <svg viewBox="0 0 100 100" width="90" height="90">
        <style>{`@keyframes pur-fill { 0%,100%{opacity:0.25} 50%{opacity:1} } .pur-c { animation: pur-fill 2.4s ease-in-out infinite; }`}</style>
        {[0,1,2,3,4].map(row => [0,1,2,3,4].map(col => (
          <rect key={`${row}-${col}`} className="pur-c"
            x={15 + col * 15} y={15 + row * 15}
            width="11" height="11" rx="2"
            fill={accent}
            style={{ animationDelay: `${(row + col) * 0.08}s` }}
          />
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

  const normalized = {
    tempo:      Math.min(avg.tempo / 200, 1),
    brightness: Math.min(avg.centroid / 5000, 1),
    energy:     Math.min(avg.rms, 1),
    mood:       Math.min(avg.zcr, 1),
  };

  const metrics = [
    { label: "Tempo",      value: normalized.tempo * 200,      suffix: " BPM", color: "rgba(163,124,217,0.8)" },
    { label: "Brightness", value: normalized.brightness * 100, suffix: "%",    color: "rgba(242,146,146,0.8)" },
    { label: "Energy",     value: normalized.energy * 100,     suffix: "%",    color: "rgba(245,188,135,0.8)" },
    { label: "Mood",       value: normalized.mood * 100,       suffix: "%",    color: "rgba(128,205,185,0.8)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

      {/* Persona card — matches your .card aesthetic */}
      {persona ? (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "1.25rem",
          padding: "1.25rem",
          borderRadius: "16px",
          background: `linear-gradient(135deg, ${visual.gradient[0]}18, ${visual.gradient[1]}10)`,
          border: `1.5px solid ${visual.accent}30`,
        }}>
          <PersonaShape personaType={persona.persona_type} accent={visual.accent} />

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{
              margin: "0 0 2px",
              fontSize: "0.65rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: visual.accent,
              fontFamily: "'Lato', sans-serif",
            }}>
              Your Music Persona
            </p>
            <h3 style={{
              margin: "0 0 4px",
              fontSize: "1.3rem",
              fontWeight: 800,
              color: "#1a1a2e",
              fontFamily: "'Lato', sans-serif",
              lineHeight: 1.15,
            }}>
              {persona.persona_type}
            </h3>
            <p style={{
              margin: "0 0 10px",
              fontSize: "0.78rem",
              color: "#777",
              fontStyle: "italic",
              fontFamily: "'Lato', sans-serif",
            }}>
              {visual.description}
            </p>

            {/* Tags — match your time-range button pill style */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {persona.persona_tags.map((tag, i) => (
                <span key={i} style={{
                  padding: "0.2rem 0.7rem",
                  borderRadius: "999px",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  fontFamily: "'Lato', sans-serif",
                  background: `${visual.accent}18`,
                  color: visual.accent,
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
        // Subtle placeholder while loading or if model not trained yet
        <div style={{
          padding: "1rem 1.25rem",
          borderRadius: "16px",
          background: "#f0f0f0",
          color: "#aaa",
          fontSize: "0.8rem",
          fontFamily: "'Lato', sans-serif",
          textAlign: "center",
        }}>
          Persona not yet assigned — run seed_and_train to generate
        </div>
      )}

      {/* Divider */}
      <div style={{ borderTop: "1px solid #f0f0f0", margin: "0 0.25rem" }} />

      {/* Doughnut charts — your original layout, unchanged */}
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
        {metrics.map((metric, idx) => {
          const data = {
            labels: [metric.label, ""],
            datasets: [{
              data: [metric.value, 100 - metric.value],
              backgroundColor: [metric.color, "rgba(0,0,0,0.04)"],
              borderWidth: 0,
            }],
          };
          const options: any = {
            cutout: "72%",
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx: any) =>
                    `${metric.label}: ${metric.value.toFixed(0)}${metric.suffix}`,
                },
              },
            },
          };
          return (
            <div key={idx} style={{ width: "105px", textAlign: "center" }}>
              <Doughnut data={data} options={options} />
              <p style={{
                marginTop: "0.5rem",
                fontSize: "0.78rem",
                color: "#2b2b2b",
                fontWeight: 600,
                fontFamily: "'Lato', sans-serif",
              }}>
                {metric.label}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}