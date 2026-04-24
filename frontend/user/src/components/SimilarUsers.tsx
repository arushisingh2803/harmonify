import { useEffect, useState } from "react";
import axios from "axios";
import MatchCard from "./MatchCard.tsx";
import "./style/SimilarUsers.css";

type SimilarUsersData = {
  my_persona: string;
  cluster_id: number;
  matches: any[];
};

const PERSONA_ACCENTS: Record<string, string> = {
  "The Seeker":    "#3B82F6",
  "The Guardian":  "#6366f1",
  "The Zealous":   "#f97316",
  "The Wistful":   "#fb923c",
  "The Formalist": "#14b8a6",
};

export default function SimilarUsers({ userId }: { userId: string }) {
  const [data, setData] = useState<SimilarUsersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    setLoading(true);
    axios
      .get(`http://localhost:8000/similar-users/?user_id=${userId}`)
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load similar users.");
        setLoading(false);
      });
  }, [userId]);

  if (loading) {
    return <div className="centered">Finding your people...</div>;
  }

  if (error) {
    return <div className="empty-state">{error}</div>;
  }

  if (!data || data.matches.length === 0) {
    return (
      <div className="empty-state">
        <p>No matches found yet</p>
        <p>More users need to join Harmonify to find your matches.</p>
      </div>
    );
  }

  const accent = PERSONA_ACCENTS[data.my_persona] ?? "#a37cd9";

  return (
    <div className="similar-users-container">
      <div
        className="similar-users-header"
        style={{
          background: `linear-gradient(135deg, ${accent}15, ${accent}08)`,
          border: `1.5px solid ${accent}25`,
        }}
      >
        <p style={{ color: accent, fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", margin: 0 }}>YOUR MATCHES</p>
        <h2>Similar Users</h2>
        <p style={{ color: "#777", margin: 0 }}>
          {data.matches.length} {data.my_persona} listener{data.matches.length !== 1 ? "s" : ""} — ranked by similarity
        </p>
      </div>

      <div className="similar-users-grid">
        {data.matches.map((match) => (
          <MatchCard key={match.user_id} match={match} />
        ))}
      </div>
    </div>
  );
}