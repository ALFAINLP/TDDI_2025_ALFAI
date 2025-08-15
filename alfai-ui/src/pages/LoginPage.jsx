import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../styles/LoginRegister.css";
import { themes, applyTheme } from "../utils/themeData";

const LoginPage = ({ setUser }) => {
  const [tc, setTc] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    applyTheme(themes[0]);
  }, []);

  const handleLogin = async () => {
    setError("");

    const response = await fetch("http://localhost:8000/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tc }),
    });

    const data = await response.json();

    if (data.success) {
      const userId = data.user_id;

      const userInfoRes = await fetch(`http://localhost:8000/api/user-info/${userId}`);
      const userInfoData = await userInfoRes.json();

      if (userInfoData.success) {
        setUser({
          userId,
          name: userInfoData.user.name,
          tc: userInfoData.user.tc,
        });
        sessionStorage.setItem("user_id", userId);
        navigate("/dashboard");
      } else {
        setError(userInfoData.message || "Kullanıcı bilgisi alınamadı");
      }
    } else {
      setError(data.message || "Bir hata oluştu");
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
          <input
            type="text"
            placeholder="T.C. Kimlik No"
            value={tc}
            onChange={(e) => setTc(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleLogin();
              }
            }}
          />
          <button className="button-30" onClick={handleLogin}>GİRİŞ</button>
          {error && <p className="error-message">{error}</p>}
          <div className="links">
            <Link to="/register" className="button-30 small-button">KAYIT OL</Link>
          </div>
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

export default LoginPage;