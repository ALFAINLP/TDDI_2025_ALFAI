import React, { useRef, useEffect, useState, useCallback } from "react";
import { FaMicrophone, FaTimes } from "react-icons/fa";
import "../styles/ChatWindow.css";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const ChatWindow = ({ user, messages, setMessages, input, setInput }) => {
  const chatEndRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [showRecorder, setShowRecorder] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [agentTyping, setAgentTyping] = useState(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(false, input);
    }
  };

  const playTTS = useCallback(async (text) => {
    try {
      const res = await fetch(`${API_BASE}/api/text-to-speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();

      if (data.success && data.audio_base64) {
        const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
        audio.play();
      } else {
        console.error("TTS başarısız:", data.error || "Bilinmeyen hata");
      }
    } catch (err) {
      console.error("TTS çağrısı hatası:", err);
    }
  }, []);

  const normalizeAgentText = (payload) => {
    if (!payload) return "";
    return payload.response ?? payload.message ?? payload.error ?? "";
  };

  const sendMessage = async (isFromSTT, messageText) => {
    if (isSending) return;
    if (!messageText || !messageText.trim()) return;

    setMessages((prev) => [...prev, { role: "user", text: messageText }]);
    setInput("");

    const userIdToSend = user?.tc || user?.userId || "";
    if (!userIdToSend) {
      console.error("User ID yok, mesaj gönderilemiyor.");
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Kimlik bilgisi bulunamadı (userId/TC)." },
      ]);
      return;
    }

    setIsSending(true);
    setAgentTyping(true);

    try {
      const res = await fetch(`${API_BASE}/api/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userIdToSend, message: messageText }),
      });

      let data = null;
      try {
        data = await res.json();
      } catch (jsonErr) {
        console.error("JSON parse hatası:", jsonErr);
      }

      if (!res.ok) {
        const txt = normalizeAgentText(data) || `Sunucu hatası: ${res.status}`;
        setMessages((prev) => [...prev, { role: "agent", text: txt }]);
        return;
      }

      const agentText = normalizeAgentText(data);
      const finalText =
        agentText && String(agentText).trim().length > 0
          ? agentText
          : "Boş yanıt alındı.";

      setMessages((prev) => [...prev, { role: "agent", text: finalText }]);

      if (isFromSTT) {
        await playTTS(finalText);
      }
    } catch (err) {
      console.error("Mesaj gönderme hatası:", err);
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "İstek gönderilirken hata oluştu." },
      ]);
    } finally {
      setIsSending(false);
      setAgentTyping(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("file", audioBlob, "input.wav");

        try {
          const res = await fetch(`${API_BASE}/transcribe`, {
            method: "POST",
            body: formData,
          });
          const data = await res.json();

          if (data?.text) {
            sendMessage(true, data.text);
          } else {
            setMessages((prev) => [
              ...prev,
              { role: "agent", text: "Ses çözümlenemedi." },
            ]);
          }
        } catch (err) {
          console.error("Ses API hatası:", err);
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: "Ses API hatası oluştu." },
          ]);
        }
        // ❌ Modal kapatma yok
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mikrofon hatası:", err);
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Mikrofon erişimi reddedildi veya başarısız." },
      ]);
      setShowRecorder(false);
    }
  };

  const stopRecording = () => {
    try {
      mediaRecorderRef.current?.stop();
    } finally {
      setIsRecording(false);
      // ❌ Modal kapatma yok
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">ALFAI ÇAĞRI MERKEZİNE HOŞ GELDİNİZ</div>

      <div className={`chat-messages ${showRecorder ? "blurred" : ""}`}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message-row ${msg.role === "user" ? "user" : "agent"}`}
          >
            <div className="message-bubble">{msg.text}</div>
          </div>
        ))}

        {agentTyping && (
          <div className="message-row agent">
            <div className="message-bubble">
              <span className="typing-dot">●</span>
              <span className="typing-dot">●</span>
              <span className="typing-dot">●</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className={`chat-input-container ${showRecorder ? "blurred" : ""}`}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Mesajınızı yazın..."
          className="chat-input"
          rows={1}
          disabled={isSending}
        />

        <button
          onClick={() => setShowRecorder(true)}
          className="mic-button"
          title="Ses Kaydı Başlat"
          disabled={isSending}
        >
          <FaMicrophone />
        </button>

        <button
          onClick={() => sendMessage(false, input)}
          className="send-button"
          disabled={isSending || !input?.trim()}
        >
          {isSending ? "Gönderiliyor..." : "Gönder"}
        </button>
      </div>

      {showRecorder && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button
              className="modal-close"
              onClick={() => {
                if (isRecording) stopRecording();
                setShowRecorder(false);
              }}
            >
              <FaTimes />
            </button>

            <h2>Sesli Sohbet</h2>
            {!isRecording ? (
              <button onClick={startRecording} className="record-button">
                Kaydı Başlat
              </button>
            ) : (
              <button onClick={stopRecording} className="stop-button">
                Kaydı Durdur & Gönder
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWindow;