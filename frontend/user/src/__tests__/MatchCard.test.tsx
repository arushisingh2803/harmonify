import { render, screen } from "@testing-library/react";
import MatchCard from "../components/MatchCard";

const mockMatch = {
  user_id: 1,
  display_name: "testuser",
  persona_type: "The Seeker",
  persona_tags: ["eclectic", "adventurous"],
  shared_genres: ["indie", "jazz"],
  shared_artists: [
    { id: "a1", name: "Artist One", image: "" },
    { id: "a2", name: "Artist Two", image: "" },
  ],
  shared_artist_count: 2,
  match_pct: 85,
};

describe("MatchCard", () => {
  it("renders the display name", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("testuser")).toBeInTheDocument();
  });

  it("renders the persona type", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("The Seeker")).toBeInTheDocument();
  });

  it("renders the match percentage", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("85% match")).toBeInTheDocument();
  });

  it("renders all persona tags", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("eclectic")).toBeInTheDocument();
    expect(screen.getByText("adventurous")).toBeInTheDocument();
  });

  it("renders shared genres", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("indie")).toBeInTheDocument();
    expect(screen.getByText("jazz")).toBeInTheDocument();
  });

  it("renders shared artist count", () => {
    render(<MatchCard match={mockMatch} />);
    expect(screen.getByText("2 shared artists")).toBeInTheDocument();
  });

  it("shows no shared genres message when empty", () => {
    const noGenresMatch = { ...mockMatch, shared_genres: [] };
    render(<MatchCard match={noGenresMatch} />);
    expect(screen.getByText("No shared genres")).toBeInTheDocument();
  });

  it("does not render shared artists section when empty", () => {
    const noArtistsMatch = {
      ...mockMatch,
      shared_artists: [],
      shared_artist_count: 0,
    };
    render(<MatchCard match={noArtistsMatch} />);
    expect(screen.queryByText("shared artist")).not.toBeInTheDocument();
  });
});