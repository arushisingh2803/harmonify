import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Homepage from "./components/Homepage.tsx";
import Dashboard from "./components/Dashboard.tsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="/dashboard" element={<RequireToken><Dashboard /></RequireToken>} />
      </Routes>
    </BrowserRouter>
  );
}

function RequireToken({ children }) {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");

  if (!token) {
    return <Navigate to="/" replace />;
  }
  return children;
}
