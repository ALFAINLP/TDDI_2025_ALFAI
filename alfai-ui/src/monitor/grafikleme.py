import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import Counter
from datetime import datetime

JSON_FILE = "/home/hpc/Desktop/agent_skeleton/agent_memory.json"

def load_data():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_tool_usage(data):
    counts = Counter([d["tool"] for d in data])
    return counts

def parse_success_counts(data):
    counts = Counter([d["status"] for d in data])
    return counts

def update(frame):
    plt.clf()
    data = load_data()
    
    # 1️⃣ Log table
    ax1 = plt.subplot2grid((2,2), (0,0))
    ax1.set_title("Log Çıktısı")
    log_text = "\n".join([f'{d["timestamp"]} | {d["user_id"]} | {d["tool"]} | {d.get("status")}' for d in data[-10:]])
    ax1.text(0, 0.5, log_text, fontsize=9, va='center')
    ax1.axis("off")
    
    # 2️⃣ Tool kullanım sayısı
    ax2 = plt.subplot2grid((2,2), (0,1))
    tool_counts = parse_tool_usage(data)
    ax2.bar(tool_counts.keys(), tool_counts.values(), color="skyblue")
    ax2.set_title("Tool Kullanım Sayısı")
    ax2.set_xticklabels(tool_counts.keys(), rotation=45, ha="right")
    
    # 3️⃣ Başarılı işlem sayısı
    ax3 = plt.subplot2grid((2,2), (1,0))
    status_counts = parse_success_counts(data)
    ax3.bar(status_counts.keys(), status_counts.values(), color="green")
    ax3.set_title("Başarılı İşlem Sayısı")
    
    # 4️⃣ Hatalar (örnek)
    ax4 = plt.subplot2grid((2,2), (1,1))
    error_counts = status_counts.get("error", 0)
    ax4.bar(["Hatalar"], [error_counts], color="red")
    ax4.set_title("Hatalar")
    
    plt.tight_layout()

ani = FuncAnimation(plt.gcf(), update, interval=5000)
plt.show()
