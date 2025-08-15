from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import whisper
import tempfile
import shutil
from gtts import gTTS
import os
import base64
import io
import matplotlib.pyplot as plt
from collections import Counter
import json
import datetime
from memory import memory
from agent_runner import main
from tools import (
    get_user_info,
    register_user,
    get_user_id_from_tc_and_verify_identity,
    get_outstanding_balance
)

app = FastAPI()
model = whisper.load_model("medium")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JSON_FILE = "/home/hpc/Desktop/agent_skeleton (8)/agent_skeleton/agent_memory.json"

# ----------------- Pydantic Modeller -----------------
class TextRequest(BaseModel):
    text: str

class LoginRequest(BaseModel):
    tc: str

class RegisterRequest(BaseModel):
    tc: str
    name: str
    email: str

class MessageRequest(BaseModel):
    user_id: str
    message: str

class MessageResponse(BaseModel):
    success: bool
    response: str = ""
    error: str = ""

# ----------------- Helper Fonksiyonlar -----------------
def load_agent_data():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_tool_usage(data):
    return Counter([d["tool"] for d in data])

def parse_success_counts(data):
    return Counter([d.get("status") for d in data])

# ----------------- API Endpoints -----------------
@app.post("/api/login")
def login(req: LoginRequest):
    tc = req.tc

    # TC kimlik doğrulaması ve user_id bulma
    result = get_user_id_from_tc_and_verify_identity(tc, tc)
    if not result["success"]:
        return {"success": False, "message": result["error"]}

    user_id = result["data"]

    # Oturumu kaydet (TC üzerinden erişim yapacak)
    memory.set_authenticated_user(tc, user_id)

    return {
        "success": True,
        "user_id": user_id,
        "message": result.get("message", "Giriş başarılı.")
    }

@app.post("/api/register")
def register(req: RegisterRequest):
    result = register_user(req.tc, req.name, req.email)
    if not result["success"]:
        return {"success": False, "message": result["error"]}
    return {"success": True, "user": result["data"]}

@app.post("/api/message", response_model=MessageResponse)
def message(req: MessageRequest):
    out = main(req.user_id, req.message)
    # main() eski dict döndürüyorsa bile normalize edelim:
    if out.get("success"):
        return MessageResponse(success=True, response=out.get("response", ""))
    else:
        return MessageResponse(success=False, error=out.get("message", out.get("error", "Bilinmeyen hata")))

@app.get("/api/user-info/{user_id}")
def user_info(user_id: str):
    result = get_user_info(user_id)
    if not result["success"]:
        return {"success": False, "message": result.get("error", "Bilinmeyen hata")}
    return {"success": True, "user": result["data"]}

@app.get("/api/outstanding-balance/{user_id}")
def outstanding_balance(user_id: str):
    result = get_outstanding_balance(user_id)
    if not result["success"]:
        return {"success": False, "message": result.get("error", "Bilinmeyen hata")}
    return {"success": True, "balance_info": result["data"]}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    result = model.transcribe(tmp_path, language="tr")
    return {"text": result["text"]}

@app.post("/api/text-to-speech")
def text_to_speech(req: TextRequest):
    try:
        tts = gTTS(text=req.text, lang="tr")
        tmp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_mp3.close()
        tts.save(tmp_mp3.name)

        with open(tmp_mp3.name, "rb") as f:
            audio_bytes = f.read()
        os.remove(tmp_mp3.name)

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {"success": True, "audio_base64": audio_b64}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- Helper Fonksiyonlar -----------------
def load_agent_data():
    """
    agent_memory.json (interactions tabanlı) -> düz kayıt listesi:
    [
      {timestamp, user_id, role, message, type, tool, status}
    ]
    """
    if not os.path.exists(JSON_FILE):
        return []

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    interactions = raw.get("interactions", {})
    flat = []
    now = datetime.datetime.now()

    def infer_status(entry_type: str) -> str:
        if entry_type == "tool":
            return "success"
        if entry_type == "tool_error":
            return "error"
        return "message"

    def extract_tool(entry: dict) -> str:
        md = entry.get("metadata") or {}
        return md.get("tool") or ""

    for user_id, items in interactions.items():
        # Zaman damgası JSON’da yok; sıraya göre sentetik üretelim
        for idx, entry in enumerate(items):
            ts = (now - datetime.timedelta(seconds=(len(items) - idx))).isoformat(timespec="seconds")
            etype = entry.get("type", "message")
            flat.append({
                "timestamp": ts,
                "user_id": user_id,
                "role": entry.get("role", ""),
                "message": entry.get("message", ""),
                "type": etype,
                "tool": extract_tool(entry),
                "status": infer_status(etype),
            })

    return flat

def parse_tool_usage(flat_data):
    # Sadece tool alanı dolu kayıtları say
    return Counter([d["tool"] for d in flat_data if d.get("tool")])

def parse_success_counts(flat_data):
    # success / error / message say
    return Counter([d.get("status", "message") for d in flat_data])

# ----------------- Matplotlib Grafikleri -----------------
@app.get("/monitor", response_class=HTMLResponse)
def monitor_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monitör</title>
    </head>
    <body style="text-align:center; background:#1f1f23; color:#fff;">
        <h1>Agent Monitör</h1>
        <img id="agent-plot" src="/api/agent-plots" style="max-width:90%; margin-top:20px;"/>
        <p style="margin-top:10px; font-size:0.9rem;">Grafikler her yenilendiğinde sayfayı refresh edin.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/agent-plots")
def get_agent_plots():
    data = load_agent_data()  # <-- Artık flattened liste
    fig = plt.figure(figsize=(10,6))
    
    # 1️⃣ Log tablosu (son 10)
    ax1 = plt.subplot2grid((2,2), (0,0))
    ax1.set_title("Log Çıktısı")
    last10 = data[-10:]
    if last10:
        lines = []
        for d in last10:
            msg = d.get("message", "")
            if len(msg) > 60:
                msg = msg[:57] + "..."
            line = f'{d["timestamp"]} | {d["user_id"]} | {d.get("tool") or "-"} | {d.get("status")} | {msg}'
            lines.append(line)
        log_text = "\n".join(lines)
    else:
        log_text = "Kayıt bulunamadı."
    ax1.text(0.0, 1.0, log_text, fontsize=9, va='top', ha='left', transform=ax1.transAxes)
    ax1.axis("off")
    
    # 2️⃣ Tool kullanım sayısı
    ax2 = plt.subplot2grid((2,2), (0,1))
    tool_counts = parse_tool_usage(data)
    ax2.set_title("Tool Kullanım Sayısı")
    if tool_counts:
        labels = list(tool_counts.keys())
        values = list(tool_counts.values())
        xs = range(len(labels))
        ax2.bar(xs, values)
        ax2.set_xticks(list(xs))
        ax2.set_xticklabels(labels, rotation=45, ha="right")
        for i, v in enumerate(values):
            ax2.text(i, v, str(v), ha='center', va='bottom', fontsize=9)
    else:
        ax2.text(0.5, 0.5, "Veri yok", ha="center", va="center")
        ax2.set_xticks([]); ax2.set_yticks([])
    
    # 3️⃣ Durum sayıları (success/error/message)
    ax3 = plt.subplot2grid((2,2), (1,0))
    status_counts = parse_success_counts(data)
    ax3.set_title("İşlem Durum Sayıları")
    if status_counts:
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        xs = range(len(labels))
        ax3.bar(xs, values)
        ax3.set_xticks(list(xs))
        ax3.set_xticklabels(labels)
        for i, v in enumerate(values):
            ax3.text(i, v, str(v), ha='center', va='bottom', fontsize=9)
    else:
        ax3.text(0.5, 0.5, "Veri yok", ha="center", va="center")
        ax3.set_xticks([]); ax3.set_yticks([])
    
    # 4️⃣ Hatalar (error)
    ax4 = plt.subplot2grid((2,2), (1,1))
    ax4.set_title("Hatalar")
    error_count = status_counts.get("error", 0) if status_counts else 0
    ax4.bar([0], [error_count])
    ax4.set_xticks([0]); ax4.set_xticklabels(["Hatalar"])
    ax4.text(0, error_count, str(error_count), ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return StreamingResponse(buf, media_type="image/png")
