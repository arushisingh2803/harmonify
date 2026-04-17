import { render, screen, fireEvent } from "@testing-library/react";
import Homepage from "../components/Homepage";

// Mock browser APIs not available in jsdom
beforeAll(() => {
  global.IntersectionObserver = class {
    constructor(cb: any) {}
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any;

  HTMLCanvasElement.prototype.getContext = () => null as any;
  jest.spyOn(console, "error").mockImplementation(() => {});
});

afterAll(() => {
  (console.error as jest.Mock).mockRestore();
});

describe("Homepage", () => {
  it("renders the Harmonify title", () => {
    render(<Homepage />);
    expect(screen.getByText("harmonify.")).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<Homepage />);
    expect(screen.getByText("your music personified.")).toBeInTheDocument();
  });

  it("renders the login button", () => {
    render(<Homepage />);
    expect(screen.getByText("Login with Spotify")).toBeInTheDocument();
  });

  it("renders all three feature items", () => {
    render(<Homepage />);
    expect(screen.getByText("your music persona")).toBeInTheDocument();
    expect(screen.getByText("your sonic circle")).toBeInTheDocument();
    expect(screen.getByText("live your sound")).toBeInTheDocument();
  });

  it("renders the footer", () => {
    render(<Homepage />);
    expect(screen.getByText("© 2026 Harmonify")).toBeInTheDocument();
  });

  it("login button triggers redirect", () => {
    delete (window as any).location;
    (window as any).location = { href: "" };
    render(<Homepage />);
    fireEvent.click(screen.getByText("Login with Spotify"));
    expect(window.location.href).toBe("http://localhost:8000/login");
  });
});