import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import Dashboard from "./pages/Dashboard";

function App() {
  const [user, setUser] = useState(null);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />

        <Route
          path="/login"
          element={
            user ? <Navigate to="/dashboard" /> : <LoginPage setUser={setUser} />
          }
        />

        <Route
          path="/register"
          element={<RegisterPage setUser={setUser} />}
        />

        <Route
          path="/dashboard"
          element={
            user ? <Dashboard user={user} /> : <Navigate to="/login" />
          }
        />
      </Routes>
    </Router>
  );
}

export default App;