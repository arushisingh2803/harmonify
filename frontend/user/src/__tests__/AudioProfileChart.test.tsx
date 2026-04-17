import { render, screen, waitFor } from "@testing-library/react";
import AudioProfileChart from "../components/AudioProfileChart";

jest.mock("axios", () => ({
  get: jest.fn(),
}));

import axios from "axios";
const mockedAxios = axios as jest.Mocked<typeof axios>;

const mockAvg = {
  tempo:    120.0,
  centroid: 3000.0,
  zcr:      0.10,
  rms:      0.20,
  mood:     4000.0,
  mfcc:     [],
};

beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterAll(() => {
  (console.error as jest.Mock).mockRestore();
});

describe("AudioProfileChart", () => {
  beforeEach(() => {
    mockedAxios.get.mockResolvedValue({
      data: {
        persona_type: "The Guardian",
        persona_tags: ["refined", "consistent"],
        cluster_id: 0,
      }
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(<AudioProfileChart avg={mockAvg} userId="1" />);
  });

  it("renders energy section", () => {
    render(<AudioProfileChart avg={mockAvg} userId="1" />);
    expect(screen.getByText("Energy")).toBeInTheDocument();
  });

  it("renders mood section", () => {
    render(<AudioProfileChart avg={mockAvg} userId="1" />);
    expect(screen.getByText("Mood")).toBeInTheDocument();
  });

  it("shows persona card after loading", async () => {
    render(<AudioProfileChart avg={mockAvg} userId="1" />);
    await waitFor(() =>
      expect(screen.getByText("The Guardian")).toBeInTheDocument()
    );
  });

  it("shows persona tags after loading", async () => {
    render(<AudioProfileChart avg={mockAvg} userId="1" />);
    await waitFor(() =>
      expect(screen.getByText("refined")).toBeInTheDocument()
    );
  });

  it("returns null when avg not provided", () => {
    const { container } = render(
      <AudioProfileChart avg={null as any} userId="1" />
    );
    expect(container.firstChild).toBeNull();
  });
});