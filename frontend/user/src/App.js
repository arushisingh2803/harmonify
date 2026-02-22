import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Homepage from "./components/Homepage.tsx";
import Dashboard from "./components/Dashboard.tsx";
import ConcertRecommendations from "./components/ConcertRecommendations.tsx";
import ConcertChat from "./components/ConcertChat.tsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="/dashboard" element={<RequireToken><Dashboard /></RequireToken>} />
        <Route path="/concerts" element={<RequireToken><ConcertRecommendations /></RequireToken>} />
        <Route path="/concerts/:concertId" element={<RequireToken><ConcertChat /></RequireToken>} />
      </Routes>
    </BrowserRouter>
  );
}

function RequireToken({ children }) {
  const token = localStorage.getItem("spotify_token");

  if (!token) {
    return <Navigate to="/" replace />;
  }

  return children;
}