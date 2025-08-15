import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";

const Dashboard = ({ user }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Önce kullanıcı mesajını ekle
    const userMessage = { role: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await fetch("http://localhost:8000/api/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.userId,
          message: input,
        }),
      });

      const data = await response.json();

      if (data.response) {
        const botMessage = { role: "bot", text: data.response };
        setMessages((prev) => [...prev, botMessage]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: "Yanıt alınamadı." },
        ]);
      }

    } catch (err) {
      console.error("Hata:", err);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Sunucu hatası oluştu." },
      ]);
    }
  };

  if (!user) return <div>Yükleniyor...</div>;

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar user={user} />
      <ChatWindow
        user={user}
        messages={messages}
        setMessages={setMessages}
        input={input}
        setInput={setInput}
        sendMessage={sendMessage}
      />
    </div>
  );
};

export default Dashboard;