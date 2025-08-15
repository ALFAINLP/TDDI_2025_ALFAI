# TEKNOFEST 2025 Türkçe Doğal Dil İşleme Yarışması Projesi - Senaryo Kategorisi (Üretken Yapay Zeka Destekli Otonom Çağrı Merkezi Senaryoları)


# Agent Skeleton (ALFAI) – README

Bu proje; **çağrı merkezi/telekom müşteri işlemleri** senaryolarını çalıştıran bir **LLM destekli ajan iskeleti** içerir. Python tarafında **LangChain + FastAPI**, ön yüzde ise **React** tabanlı bir arayüz (`alfai-ui`) bulunur. LLM olarak varsayılan **Ollama** üzerinden `qwen3:32b` kullanılır. Veriler için **SQLite** (`alfai.db`) kullanılır.

> Not: Bu dosya, `agent_skeleton/` klasör yapısına ve kodlara bakılarak otomatik hazırlanmıştır. Projenize göre başlık ve ayrıntıları dilediğiniz gibi düzenleyin.

---

## İçindekiler
- [Önkoşullar](#önkoşullar)
- [Kurulum (Backend)](#kurulum-backend)
- [Veritabanı (SQLite) Kurulumu](#veritabanı-sqlite-kurulumu)
- [LLM ve Ollama](#llm-ve-ollama)
- [Çalıştırma](#çalıştırma)
- [Ön Yüz (React) – alfai-ui](#ön-yüz-react--alfai-ui)
- [Yapı ve Önemli Dosyalar](#yapı-ve-önemli-dosyalar)
- [Araçlar (tools.py) ve Senaryolar](#araçlar-toolspy-ve-senaryolar)
- [GPU Seçimi](#gpu-seçimi)
- [Sık Karşılaşılan Sorunlar](#sık-karşılaşılan-sorunlar)
- [Lisans](#lisans)

---

## Önkoşullar

- **Python 3.10+** (önerilen)
- **Node.js 18+** ve **npm** (ön yüz için)
- **Ollama** (LLM servisi; `qwen3:32b` modelini çekecek)
- **Git** (opsiyonel)
- **FFmpeg** (Whisper için önerilir)
- **CUDA** sürücüleri (GPU kullanacaksanız)

---

## Kurulum (Backend)

Projeyi klonladıktan/çıkardıktan sonra `agent_skeleton/agent_skeleton` klasöründe bir sanal ortam oluşturup bağımlılıkları kurun.

```bash
# sanal ortam (örnek: venv)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# bağımlılıklar
pip install --upgrade pip

# Çekirdek paketler (projeden tespit edilenlere göre)
pip install fastapi uvicorn langchain langchain-community langchain-ollama pydantic==2.*             openai-whisper gTTS matplotlib python-multipart

# Eğer hata alırsanız:
# pip install "pydantic<3" "langchain-community>=0.3.0" "langchain-ollama>=0.2.0"
```

> Not: Projede `requirements.txt` bulunmadı; yukarıdaki liste `api.py`, `agent_runner.py`, `tools.py` ve benzerlerinden türetilmiştir. Lokal ortamınıza göre ek paketler (ör. `sqlite3` stdlib ile gelir) gerekebilir.

---

## Veritabanı (SQLite) Kurulumu

Backend, `agent_skeleton/agent_skeleton/mock_apis.py` içinde **`DB_PATH = "alfai.db"`** kullanır. Bu dosyanın yanında bir SQLite DB beklenir. Aşağıdaki örnek şema ile boş bir **`alfai.db`** oluşturabilirsiniz:

Hızlı başlangıç için Python ile oluşturma:

```bash
python - <<'PY'
import sqlite3, os, json, uuid, datetime as dt
db = "alfai.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

schema = open("schema.sql","w",encoding="utf-8"); schema.write("""<yukarıdaki SQL'i buraya yapıştırın>"""); schema.close()
with open("schema.sql","r",encoding="utf-8") as f:
    cur.executescript(f.read())

# Örnek veri:
cur.execute("INSERT OR IGNORE INTO users (user_id, tc, name, email, package, package_id, line_status) VALUES (?,?,?,?,?,?,?)",
            ("u-1001","11111111111","Deneme Kullanıcı","deneme@example.com","Fiber 100","pkg-100","active"))
cur.execute("INSERT OR IGNORE INTO packages (package_id,name,price,details,data_cap_gb) VALUES (?,?,?,?,?)",
            ("pkg-100","Fiber 100",299.9,"100 Mbps, limitsiz",None))
cur.execute("INSERT OR IGNORE INTO packages (package_id,name,price,details,data_cap_gb) VALUES (?,?,?,?,?)",
            ("pkg-200","Fiber 200",399.9,"200 Mbps, limitsiz",None))
conn.commit(); conn.close()
print("alfai.db hazır.")
PY
```

> Tablo adları `mock_apis.py` içinde kullanılan sorgulara göre belirlenmiştir: `users`, `packages`, `campaigns`, `users_campaigns`, `support_tickets`, `bills`, `billing_disputes`, `package_requests`, `feedbacks`.

---

## LLM ve Ollama

1. Ollama’yı kurun: https://ollama.com
2. Modeli indirin:
   ```bash
   ollama pull qwen3:32b
   ```
3. Backend tarafında varsayılan model `qwen3:32b` olarak ayarlanmıştır (bkz. `agent_runner.py`). Gerekirse değiştirin.

> LoRA/adapter kullanıyorsanız kendi `Modelfile` ile modelinizi `ollama create` komutu üzerinden oluşturabilirsiniz.

---

## Çalıştırma

### 1) API (FastAPI)
Proje kökünde **`agent_skeleton/agent_skeleton/`** klasörüne gidin:

```bash
# .env (opsiyonel) oluşturup yapılandırabilirsiniz
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
veya doğrudan örnek script:
```bash
python agent_runner.py
```

> `api.py` içinde `/api/message` gibi uç noktalar; `agent_runner.py` içinde LLM ajan akışı ve araç entegrasyonları bulunur.

### 2) Test Senaryoları
- `scenarios.json`: Ajanın deneme diyalogları ve tool zinciri kurguları.
- `agent_memory.json`: Basit hafıza örneği.

---

## Ön Yüz (React) – `alfai-ui`

Klasör: `agent_skeleton/agent_skeleton/alfai-ui`

```bash
cd alfai-ui
npm install
npm start
```
Varsayılan komutlar `package.json` içinde mevcuttur. Gerekirse API adresini `.env` veya kod içinde güncelleyin.

---

## Yapı ve Önemli Dosyalar

- `agent_runner.py` — LangChain ajanı, araç kaydı ve akış.
- `api.py` — FastAPI servis uçları (metin/ses işleme vb.).
- `tools.py` — İş mantığı sarmalayan **StructuredTool** tanımları.
- `tool_registry.py` — Araç kayıt/metadata.
- `memory.py` — `AgentMemory` ve bellek yardımcıları.
- `mock_apis.py` — SQLite tabanlı sahte servisler (kullanıcı, paket, fatura, kampanya, ticket).
- `scenarios.json` — Test senaryoları.
- `agent_memory.json` — Örnek bellek dosyası.
- `alfai-ui/` — React arayüzü.

---

## Araçlar (`tools.py`) ve Senaryolar

- Araçlar; paket değişimi, fatura itirazı, ek paket talebi, kampanya katılımı, destek bileti, bakiye ödeme vb. fonksiyonları `mock_apis.py` üstünden yürütür.
- `scenarios.json` senaryoları; intent, tool zinciri, cevap türü ve bellek anahtarlarıyla gelir.
- **Önemli Not:** Bazı projelerde `register`/`tc` akışları devre dışı bırakılabilir. Kendi veritabanınıza göre `tools.py` çağrılarını ve senaryoları düzenleyin.

---

## GPU Seçimi

Sadece **Ollama sunucusunun** göreceği şekilde **CUDA** GPU seçebilirsiniz.

```bash
# Örn. sadece GPU 2'yi görünür yap
export CUDA_VISIBLE_DEVICES=2        # Windows PowerShell: $env:CUDA_VISIBLE_DEVICES="2"
ollama serve
```

> Model tarafında ek ayar gerekiyorsa (örn. `num_gpu`, `num_ctx`), Ollama servis konfigürasyonu veya Modelfile üzerinden yapılandırın.

---

## Lisans

Bu proje için lisans bilgisi ekleyin (MIT/Apache-2.0 vb.).
