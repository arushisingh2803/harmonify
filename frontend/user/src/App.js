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
  const userId = params.get("user_id") || localStorage.getItem("harmonify_user_id");
  if (!userId) return <Navigate to="/" replace />;
  return children;
}