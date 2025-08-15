# TEKNOFEST 2025 Türkçe Doğal Dil İşleme Yarışması Projesi - Senaryo Kategorisi (Üretken Yapay Zeka Destekli Otonom Çağrı Merkezi Senaryoları)


# Agent Skeleton (ALFAI) – README

Bu proje; **çağrı merkezi/telekom müşteri işlemleri** senaryolarını çalıştıran bir **LLM destekli ajan iskeleti** içerir. Python tarafında **LangChain + FastAPI**, ön yüzde ise **React** tabanlı bir arayüz (`alfai-ui`) bulunur. LLM olarak varsayılan **Ollama** üzerinden `qwen3:32b` kullanılır. Veriler için **SQLite** (`alfai.db`) kullanılır.

---

## Önkoşullar

- **Python 3.10+** (önerilen)
- **Node.js 16+** ve **npm** (ön yüz için)
- **Ollama** (LLM servisi; `qwen3:32b` modelini çekecek)
- **Git** (opsiyonel)
- **FFmpeg** (Whisper için önerilir)
- **CUDA** sürücüleri (GPU kullanacaksanız)

---

## Kurulum

```bash

git clone https://github.com/your-repository-url.git
cd agent_skeleton/agent_skeleton

# bağımlılıklar
pip install --upgrade pip

pip install fastapi uvicorn langchain langchain-community langchain-ollama pydantic==2.* openai-whisper gTTS matplotlib python-multipart

python -m venv .venv
source .venv/bin/activate   # Windows için: .venv\Scripts\activate

cd ../alfai-ui
npm install

cd ../agent_skeleton
uvicorn api:app --reload

(Farklı bir CMD'de)

cd alfai-ui
npm start

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
Proje kökünde **`agent_skeleton/`** klasörüne gidin:

```bash
# .env (opsiyonel) oluşturup yapılandırabilirsiniz
uvicorn api:app --reload
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

Klasör: `agent_skeleton/alfai-ui`

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
