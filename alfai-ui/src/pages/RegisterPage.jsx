import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/LoginRegister.css";
import { themes, applyTheme } from "../utils/themeData";
import { Link } from "react-router-dom";

const RegisterPage = ({ setUser }) => {
  const [tc, setTc] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    applyTheme(themes[0]);
  }, []);

  const handleRegister = async () => {
    setError("");

    const response = await fetch("http://localhost:8000/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tc, name, email }),
    });

    const data = await response.json();

    if (data.success) {
      const user = {
        userId: data.user.user_id,
        name: data.user.name,
        tc: data.user.tc,
      };
      setUser(user);
      navigate("/dashboard");
    } else {
      setError(data.message || "Kayıt sırasında hata oluştu.");
    }
  };

  return (
    <div className="container">
      <div className="form-wrapper">
        <div className="circle circle-one" />
        <img
          className="illustration"
          src="https://raw.githubusercontent.com/hicodersofficial/glassmorphism-login-form/master/assets/illustration.png"
          alt="illustration"
        />
        <div className="form-container">
          <input type="text" placeholder="T.C. Kimlik No" value={tc} onChange={(e) => setTc(e.target.value)} />
          <input type="text" placeholder="Ad Soyad" value={name} onChange={(e) => setName(e.target.value)} />
          <input type="email" placeholder="E-posta" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button onClick={handleRegister}>KAYIT OL</button>
          {error && <p className="error-message">{error}</p>}

          <Link to="/" className="button-30 small-button">GİRİŞ YAP</Link>
        </div>
        <div className="circle circle-two" />
        <div className="theme-btn-container">
          {themes.map((t, i) => (
            <div
              key={i}
              className="theme-btn"
              style={{ background: t.background }}
              onClick={() => applyTheme(t)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;