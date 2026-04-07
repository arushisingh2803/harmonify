import "./style/SimilarUsers.css";

type Match = {
  user_id: number;
  display_name: string;
  persona_type: string;
  persona_tags: string[];
  shared_genres: string[];
  shared_artist_count: number;
  match_pct: number;
};

const PERSONA_ACCENTS: Record<string, string> = {
  "The Seeker": "#3B82F6",
  "The Guardian": "#6366f1",
  "The Zealous": "#f97316",
  "The Wistful": "#fb923c",
  "The Socialite": "#ec4899",
  "The Formalist": "#14b8a6",
};

export default function MatchCard({ match }: { match: Match }) {
  const accent = PERSONA_ACCENTS[match.persona_type] ?? "#a37cd9";

  return (
    <div
      className="match-card"
      style={{ border: `1px solid ${accent}20` }}
    >
      <div className="match-top">
        <div>
          <p className="match-label">Harmonify User</p>
          <h3 className="match-name">{match.display_name}</h3>
        </div>

        <div
          className="match-badge"
          style={{
            background: `${accent}18`,
            border: `1px solid ${accent}40`,
            color: accent,
          }}
        >
          {match.match_pct}% match
        </div>
      </div>

      <div className="persona-row">
        <span
          className="persona-dot"
          style={{ background: accent }}
        />
        <span style={{ color: accent, fontWeight: 700 }}>
          {match.persona_type}
        </span>
      </div>

      {match.persona_tags.length > 0 && (
        <div className="tags">
          {match.persona_tags.map((tag, i) => (
            <span
              key={i}
              className="tag"
              style={{
                background: `${accent}12`,
                color: accent,
                border: `1px solid ${accent}30`,
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="divider" />

      {match.shared_genres.length > 0 ? (
        <div>
          <p className="shared-label">Shared genres</p>
          <div className="tags">
            {match.shared_genres.map((g, i) => (
              <span key={i} className="shared-chip">
                {g}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p style={{ fontStyle: "italic", color: "#bbb" }}>
          No shared genres
        </p>
      )}

      {match.shared_artist_count > 0 && (
        <p style={{ color: "#888" }}>
          {match.shared_artist_count} shared artist
          {match.shared_artist_count > 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}