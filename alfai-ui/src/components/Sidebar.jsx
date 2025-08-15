import React, { useState } from "react";

const Sidebar = ({ userInfo, outstandingBalance }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [monitorOpen, setMonitorOpen] = useState(false); // MODAL aç/kapat
  const userId = sessionStorage.getItem("user_id");

  const handleLogout = () => {
    sessionStorage.clear();
    window.location.href = "/login";
  };

  return (
    <div
      style={{
        width: "260px",
        backgroundColor: "#1f1f23",
        color: "#f0f0f0",
        height: "100vh",
        padding: "1rem",
        boxShadow: "2px 0 10px rgba(0,0,0,0.3)",
        position: "relative",
      }}
    >
      <div
        style={{
          fontSize: "1.8rem",
          cursor: "pointer",
          color: "#ff8c00",
          marginBottom: "1rem",
          userSelect: "none",
        }}
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        ☰ Menü
      </div>

      <div
        style={{
          maxHeight: menuOpen ? "1000px" : "0px",
          overflow: "hidden",
          transition: "max-height 0.5s ease-in-out",
        }}
      >
        <button
          onClick={() => setMonitorOpen(true)} // MONİTÖR modal aç
          style={{
            backgroundColor: "#ff8c00",
            color: "#fff",
            border: "none",
            padding: "10px 15px",
            borderRadius: "25px",
            cursor: "pointer",
            width: "100%",
            fontSize: "1rem",
            fontWeight: "bold",
            marginBottom: "1rem",
            transition: "background 0.3s, transform 0.1s",
          }}
          onMouseOver={(e) => (e.target.style.backgroundColor = "#1c5db8")}
          onMouseOut={(e) => (e.target.style.backgroundColor = "#ff8c00")}
        >
          📊 Monitör
        </button>

        {userInfo && (
          <div
            style={{
              background: "rgba(58, 61, 66, 0.9)",
              borderRadius: "15px",
              padding: "1.2rem",
              marginBottom: "1.5rem",
            }}
          >
            <div>
              <strong>İsim:</strong> {userInfo.name}
            </div>
            <div>
              <strong>TC:</strong> {userInfo.tc}
            </div>
            <div>
              <strong>E-posta:</strong> {userInfo.email}
            </div>
            <div>
              <strong>Paket:</strong> {userInfo.package}
            </div>
            <div>
              <strong>Paket ID:</strong> {userInfo.package_id}
            </div>
            {outstandingBalance && (
              <div
                style={{
                  marginTop: "1rem",
                  padding: "0.8rem",
                  background: "#ff4444",
                  borderRadius: "10px",
                  fontWeight: "bold",
                  textAlign: "center",
                }}
              >
                {outstandingBalance}
              </div>
            )}
          </div>
        )}

        <button
          onClick={handleLogout}
          style={{
            backgroundColor: "#e63946",
            color: "#fff",
            border: "none",
            padding: "12px 15px",
            borderRadius: "25px",
            cursor: "pointer",
            width: "100%",
            fontSize: "1rem",
            fontWeight: "bold",
          }}
        >
          ÇIKIŞ YAP
        </button>
      </div>

      {/* MONİTÖR MODAL */}
      {monitorOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0,0,0,0.6)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 9999,
          }}
          onClick={() => setMonitorOpen(false)} // overlay tıklayınca kapanır
        >
          <div
            style={{
              backgroundColor: "#1f1f23",
              borderRadius: "15px",
              padding: "1rem",
              width: "90%",
              maxWidth: "1200px",
              maxHeight: "90%",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()} // iç tıklamayı kapatmayı engeller
          >
            <h2 style={{ textAlign: "center", color: "#fff" }}>
              Agent Monitör
            </h2>
            <iframe
              src="http://localhost:8000/monitor"
              style={{ width: "100%", height: "600px", border: "none" }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;