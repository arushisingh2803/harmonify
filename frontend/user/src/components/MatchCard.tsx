import "./style/SimilarUsers.css";

type SharedArtist = {
  id: string;
  name: string;
  image: string;
};

type Match = {
  user_id: number;
  display_name: string;
  persona_type: string;
  persona_tags: string[];
  shared_genres: string[];
  shared_artists: SharedArtist[];
  shared_artist_count: number;
  match_pct: number;
};

const PERSONA_ACCENTS: Record<string, string> = {
  "The Seeker":    "#3B82F6",
  "The Guardian":  "#6366f1",
  "The Zealous":   "#f97316",
  "The Wistful":   "#fb923c",
  "The Socialite": "#ec4899",
  "The Formalist": "#14b8a6",
};

function ArtistBubbles({ artists, accent }: { artists: SharedArtist[]; accent: string }) {
  const visible  = artists.slice(0, 5);
  const overflow = artists.length - visible.length;
  const SIZE     = 36;
  const OVERLAP  = 10;
  const totalW   = visible.length * (SIZE - OVERLAP) + OVERLAP + (overflow > 0 ? SIZE : 0);

  return (
    <div className="artist-bubbles-wrapper">
      <div className="artist-bubbles" style={{ width: totalW }}>
        {visible.map((artist, i) => (
          <div
            key={artist.id}
            className="artist-bubble"
            style={{ left: i * (SIZE - OVERLAP), zIndex: visible.length - i }}
            title={artist.name}
          >
            {artist.image ? (
              <img
                src={artist.image}
                alt={artist.name}
                className="artist-bubble-img"
              />
            ) : (
              <div
                className="artist-bubble-fallback"
                style={{ background: `${accent}30`, color: accent }}
              >
                {artist.name.charAt(0)}
              </div>
            )}
          </div>
        ))}

        {/* Overflow badge */}
        {overflow > 0 && (
          <div
            className="artist-bubble artist-bubble-overflow"
            style={{
              left: visible.length * (SIZE - OVERLAP),
              background: `${accent}18`,
              color: accent,
              border: `2px solid ${accent}40`,
              zIndex: 0,
            }}
          >
            +{overflow}
          </div>
        )}
      </div>

      {/* Names below bubbles */}
      <div className="artist-names">
        {visible.map((artist, i) => (
          <span key={artist.id} className="artist-name-chip">
            {artist.name}{i < visible.length - 1 ? "," : ""}
          </span>
        ))}
        {overflow > 0 && (
          <span className="artist-name-chip">+{overflow} more</span>
        )}
      </div>
    </div>
  );
}

export default function MatchCard({ match }: { match: Match }) {
  const accent = PERSONA_ACCENTS[match.persona_type] ?? "#a37cd9";

  return (
    <div className="match-card" style={{ border: `1px solid ${accent}20` }}>

      {/* Top row */}
      <div className="match-top">
        <div>
          <p className="match-label">Spotify User</p>
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

      {/* Persona */}
      <div className="persona-row">
        <span className="persona-dot" style={{ background: accent }} />
        <span className="persona-name" style={{ color: accent }}>
          {match.persona_type}
        </span>
      </div>

      {/* Tags */}
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

      {/* Shared genres */}
      {match.shared_genres.length > 0 ? (
        <div>
          <p className="shared-label">Shared genres</p>
          <div className="tags">
            {match.shared_genres.map((g, i) => (
              <span key={i} className="shared-chip">{g}</span>
            ))}
          </div>
        </div>
      ) : (
        <p className="no-shared">No shared genres</p>
      )}

      {/* Shared artists */}
      {match.shared_artists.length > 0 && (
        <div>
          <p className="shared-label">
            {match.shared_artist_count} shared artist
            {match.shared_artist_count > 1 ? "s" : ""}
          </p>
          <ArtistBubbles artists={match.shared_artists} accent={accent} />
        </div>
      )}

    </div>
  );
}