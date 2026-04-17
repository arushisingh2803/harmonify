import { render, screen, waitFor } from "@testing-library/react";
import SimilarUsers from "../components/SimilarUsers";

jest.mock("axios", () => ({
  get: jest.fn(),
}));

import axios from "axios";
const mockedAxios = axios as jest.Mocked<typeof axios>;

const mockMatches = {
  data: {
    my_persona: "The Guardian",
    cluster_id: 0,
    matches: [
      {
        user_id: 2,
        display_name: "user2",
        persona_type: "The Guardian",
        persona_tags: ["refined"],
        shared_genres: ["indie"],
        shared_artists: [],
        shared_artist_count: 0,
        match_pct: 78,
        distance: 2.1,
      },
    ],
  },
};

describe("SimilarUsers", () => {
  beforeEach(() => {
    mockedAxios.get.mockResolvedValue(mockMatches);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading state initially", () => {
    render(<SimilarUsers userId="1" />);
    expect(screen.getByText("Finding your people...")).toBeInTheDocument();
  });

  it("renders matches after loading", async () => {
    render(<SimilarUsers userId="1" />);
    await waitFor(() =>
      expect(screen.getByText("user2")).toBeInTheDocument()
    );
  });

  it("renders the persona header", async () => {
    render(<SimilarUsers userId="1" />);
    await waitFor(() =>
      expect(screen.getByText(/The Guardian listener/)).toBeInTheDocument()
    );
  });

  it("shows empty state when no matches", async () => {
    mockedAxios.get.mockResolvedValue({
      data: { my_persona: "The Guardian", cluster_id: 0, matches: [] }
    });
    render(<SimilarUsers userId="1" />);
    await waitFor(() =>
      expect(screen.getByText("No matches found yet")).toBeInTheDocument()
    );
  });

  it("shows error state on API failure", async () => {
    mockedAxios.get.mockRejectedValue(new Error("API error"));
    render(<SimilarUsers userId="1" />);
    await waitFor(() =>
      expect(screen.getByText("Could not load similar users.")).toBeInTheDocument()
    );
  });
});