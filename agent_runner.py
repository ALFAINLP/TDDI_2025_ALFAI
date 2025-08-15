from langchain.agents import initialize_agent, AgentType, Tool
from langchain_community.llms import Ollama
from langchain.agents.agent import AgentExecutor
from functools import partial
from tool_registry import tool_registry
from tools import get_user_id_from_tc_and_verify_identity, get_user_info
from memory import AgentMemory
import re
from typing import Dict, Any, Callable
import json
from enum import Enum

from tools import (
    initiate_package_change,
    get_package_information,
    get_available_packages,
    get_bill_info,
    cancel_current_package,
    get_user_info,
    request_additional_package,
    initiate_billing_dispute,
    get_line_status,
    create_support_ticket,
    register_user,
    join_campaign,
    get_campaigns,
    get_ticket_status,
    cancel_support_ticket,
    get_outstanding_balance,
    pay_bill,
    get_package_id_by_name,
    submit_feedback,
    general_question,
    get_user_id_from_tc_and_verify_identity
)


memory = AgentMemory()
CURRENT_CONTEXT: Dict[str, Any] = {"user_id": None}
# Modeli deterministik tutun
llm = Ollama(model="qwen3:32B", base_url="http://localhost:11434", temperature=0.0)
policy_llm = Ollama(model="qwen3:32B", base_url="http://localhost:11434", temperature=0.0)

class IntentType(str, Enum):
    CAMPAIGN_JOIN = "kampanyaya_katil"
    CAMPAIGN_GET = "kampanya_bilgisini_al"
    PACKAGE_INFO = "paket_bilgi_al"
    CUSTOMER_INFO_UPDATE = "musteri_bilgi_güncelle"
    VERIFY_IDENTITY = "kimlik_doğrulama"
    TECH_SUPPORT = "teknik_destek"
    PACKAGE_LIST = "paket_listesi_al"
    PACKAGE_CHANGE = "paket_degistir"
    BILLING_INFO = "fatura_bilgisi"
    CANCEL_PACKAGE = "paket_iptali"
    USER_INFO = "kullanıcı_bilgisi"
    ADDITIONAL_PACKAGE = "ek_paket"
    BILLING_DISPUTE = "fatura_itirazı"
    LINE_STATUS = "hat_durumu"
    FIND_USER_BY_TC = "tc_ile_kullanici_bul"
    CURRENT_TICKET_STATUS = "güncel_destek_durumu"
    CANCEL_SUPPORT_TICKET = "destek_iptali"
    GET_OUTSTANDING_BALANCE = "ödenmemiş_toplam_bakiye"
    PAY_BILL = "fatura_ödeme"
    ID_FROM_PACKAGE_NAME = "paket_adından_id_belirleme"
    USER_FEEDBACK = "kullanıcı_geri_bildirimi"
    GENERAL_QUESTION = "general_question"


intent_to_tool: Dict[IntentType, Callable[..., Any]] = {
    IntentType.PACKAGE_CHANGE: initiate_package_change,
    IntentType.PACKAGE_INFO: get_package_information,
    IntentType.PACKAGE_LIST: get_available_packages,
    IntentType.BILLING_INFO: get_bill_info,
    IntentType.CANCEL_PACKAGE: cancel_current_package,
    IntentType.USER_INFO: get_user_info,
    IntentType.ADDITIONAL_PACKAGE: request_additional_package,
    IntentType.BILLING_DISPUTE: initiate_billing_dispute,
    IntentType.LINE_STATUS: get_line_status,
    IntentType.TECH_SUPPORT: create_support_ticket,
    IntentType.CUSTOMER_INFO_UPDATE: register_user,
    IntentType.CAMPAIGN_JOIN: join_campaign,
    IntentType.CAMPAIGN_GET: get_campaigns,
    IntentType.CURRENT_TICKET_STATUS: get_ticket_status,
    IntentType.CANCEL_SUPPORT_TICKET: cancel_support_ticket,
    IntentType.GET_OUTSTANDING_BALANCE: get_outstanding_balance,
    IntentType.PAY_BILL: pay_bill,
    IntentType.ID_FROM_PACKAGE_NAME: get_package_id_by_name,
    IntentType.USER_FEEDBACK: submit_feedback,
    IntentType.GENERAL_QUESTION: general_question
}
supported_intents = [i.value for i in IntentType]


def call_tool_function(func, params, *args, **kwargs):
    # Tek argüman JSON-string/dict ise ayrıştır
    if len(args) == 1 and not kwargs:
        if isinstance(args[0], str):
            try:
                parsed = json.loads(args[0])
                if isinstance(parsed, dict):
                    kwargs = parsed
                    args = ()
            except Exception:
                pass
        elif isinstance(args[0], dict):
            kwargs = args[0]
            args = ()

    # user_id otomatik ekle
    if "user_id" in params and not kwargs.get("user_id"):
        kwargs["user_id"] = CURRENT_CONTEXT.get("user_id")

    call_args = {}
    for i, p in enumerate(params):
        if i < len(args):
            call_args[p] = args[i]
        elif p in kwargs:
            call_args[p] = kwargs[p]
        else:
            call_args[p] = None

    if isinstance(call_args, str):
        return func(call_args)
    else:
        return func(**call_args)

def _field_names_from_args_schema(args_schema):
    """
    Pydantic v1 ve v2 ile uyumlu alan isimlerini döndür.
    """
    if hasattr(args_schema, "model_fields"):
        return list(args_schema.model_fields.keys())
    elif hasattr(args_schema, "_fields_"):
        return list(args_schema._fields_.keys())
    # Dataclass veya custom?
    elif hasattr(args_schema, "fields"):
        return list(getattr(args_schema, "fields").keys())
    else:
        fields = []
    return fields

def make_tools_from_registry(registry):
    tools = []
    for entry in registry:
        param_names = _field_names_from_args_schema(entry.args_schema)
        bound = partial(call_tool_function, entry.func, param_names)
        tools.append(
            Tool(
                name=entry.name,
                description=entry.description,
                func=bound
            )
        )
    return tools

tools = make_tools_from_registry(tool_registry)

# Çıkışı disipline eden ek kurallar
STRICT_PREFIX = f"""Sen bir ReAct ajanısın. Sadece iki biçimde yanıt ver:
1) Araç çağrısı gerekiyorsa:
Action: <tool_name>
Action Input: <JSON>

2) Nihai kullanıcı yanıtı verilecekse:
Final Answer: <metin>

Düşüncelerini yazma. <think> blokları üretme. Kod bloğu () veya başlık kullanma.
Eğer kullanıcı T.C. kimlik numarası gibi görünen bir sayı verirse, geçerlilik kontrolünü kendi yapma; her zaman tool_get_user_id_from_tc aracını kullan
Sadece 05 ile başlayan sayıları phone_number(telefon numarası) olarak algıla, diğerlerini algılama.
Kendin parametre adı oluşturma parametre adlı sabit kalsın. 
Parametre eksik olduğunda kullanıcıya sormayı unutma.
Eğer kullanıcı geçmek istediği paketin ID’sini verirse (örnek 'P3'), initiate_package_change aracını çağır ve 'user_id' ile 'package_id' parametrelerini doldur.
Kayıt işlemi olacağı zaman kendin bilgi doldurma kullanıcıdan cevap bekle.
Başladığın tool tamamlanmadan kullanıcı bir şey yazıyorsa o tooldan devam et. 

"""

SYSTEM_PROMPT_TR = """Rolün: Bir çağrı merkezi asistanısın. Amacın, kullanıcıyla yürüttüğün diyaloğun bağlamını korumak, ani konu değişimlerini yönetmek ve yarım kalan işlemleri gerektiğinde tamamlamaktır.
Davranış Kuralları:
- Bağlamı Takip Et: Kullanıcı farklı konuya geçerse mevcut süreci askıya al, yeni konuyu tamamla, sonra askıdakine geri dön.
- Konu Değişimi Yönetimi: Örn. paket değiştirirken kullanıcı “paket bilgilerimi öğrenmek istiyorum” derse önce paket bilgilerini ver, sonra paket değişikliğine devam et.
- Askıdaki süreçleri hafızada tut ve geri dönmeyi unutma.
- Kesinti Yönetimi: Sohbet kesilir/yanıt gecikirse, eksik bilgiyi hatırlat ve kaldığın yerden devam et.
- Girdi Anlamlandırma: Araç çalışırken kullanıcıdan istenen girdiler verildiğinde, girdinin amacını hatırla ve doğru araca aktar; başka yere yönlendirme. (Örn. “2025 Mayıs” fatura itirazı içinse doğrudan ilgili araca ilet.)
- Öncelik Sırası: Her zaman kullanıcının en son belirttiği isteği öncele. Önceki işlem, yeni konu bitince sürdürülür.
- Netlik: Her yanıt mevcut aşamayı ve bir sonraki adımı net belirtmelidir.
- Araç Çağırma: Gerekli aracı doğru sırada ve doğru parametrelerle çağır.
- Tüm araç çağrılarında parametreleri args_schema’ya uygun JSON formatında ver. 
Örnek:
{"user_id": "12345", "package_name": "Fiber 100 Mbps"}
"""

def _safe_template(s: str) -> str:
    return s.replace("{", "{{").replace("}", "}}")


def build_agent(prefix_extra: str = ""):
    full_prefix = SYSTEM_PROMPT_TR.strip()
    if prefix_extra:
        full_prefix += "\n" + prefix_extra.strip()

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        memory=memory,
        early_stopping_method="generate",
        max_iterations=4,
        agent_kwargs={"prefix": _safe_template(full_prefix)},
        handle_parsing_errors=True,
    )
    return agent


SUPERVISOR_PROMPT = _safe_template("""
Aşağıdaki konuşma durumu ve son kullanıcı mesajını değerlendir:
- current_task: Şu anda yürüyen işlem/niyet (boş olabilir)
- suspended_task: Askıya alınmış önceki işlem/niyet (boş olabilir)
- pending_params: Devam eden araç adımı için beklenen parametreler (liste/boş)

Görevlerin:
1) Kullanıcı yeni bir konu başlattıysa "decision" = "ContextSwitch" de.
2) Kullanıcı aslında beklenen parametreyi sağladıysa "decision" = "InputForRunningTool" de.
3) Aksi halde "decision" = "NoChange".

Ayrıca şunları raporla:
- "should_apply_system_prompt": (true/false) Bağlam değişimi/askıya alma/geri dönme veya girdi-amaç eşleme mantığı devreye girmeli mi?
- "notes": Kısa gerekçe.

ÇIKTIYI SADECE JSON olarak ver:
{{
  "decision": "ContextSwitch|InputForRunningTool|NoChange",
  "should_apply_system_prompt": true|false,
  "detected_new_intent": "<varsa yeni niyet/konu veya ''>",
  "notes": "<kısa açıklama>"
}}

--- STATE ---
current_task: {current_task}
suspended_task: {suspended_task}
pending_params: {pending_params}

--- USER ---
message: {user_message}
""")


def run_supervisor(user_message: str) -> Dict[str, Any]:
    uid = CURRENT_CONTEXT.get("user_id")
    current_task = memory.get_context(uid, "current_task") if uid else ""
    suspended_task = memory.get_context(uid, "suspended_task") if uid else ""
    pending_params = memory.get_context(uid, "pending_params") if uid else []

    prompt = SUPERVISOR_PROMPT.format(
        current_task=current_task or "",
        suspended_task=suspended_task or "",
        pending_params=json.dumps(pending_params or []),
        user_message=user_message
    )

    resp = policy_llm(prompt)
    try:
        data = json.loads(resp)
    except Exception:
        data = {
            "decision": "NoChange",
            "should_apply_system_prompt": False,
            "detected_new_intent": "",
            "notes": "parse_error"
        }

    if data.get("decision") == "ContextSwitch" and current_task:
        memory.set_context(uid, "suspended_task", current_task)
        memory.set_context(uid, "current_task", data.get("detected_new_intent") or "context_switch")
    elif data.get("decision") == "InputForRunningTool":
        memory.set_context(uid, "current_task", current_task or "running_tool")

    return data


def sanitize_llm_text(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r".*?", "", text, flags=re.DOTALL)  # üçlü çit bloklarını at
    return text.strip()

def is_valid_tc_format(tc: str) -> bool:
    if not tc.isdigit() or len(tc) != 11 or tc[0] == '0':
        return False
    digits = list(map(int, tc))
    if sum(digits[:10]) % 10 != digits[10]:
        return False
    if ((sum(digits[::2][:5]) * 7) - sum(digits[1::2][:4])) % 10 != digits[9]:
        return False
    return True

def _strip_think(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

def main(user_id_or_tc: str, message: str) -> Dict[str, Any]:
    try:
        if isinstance(user_id_or_tc, str) and len(user_id_or_tc) == 11 and user_id_or_tc.isdigit():
            result = get_user_id_from_tc_and_verify_identity(
                tc=user_id_or_tc,
                challenge_response=user_id_or_tc
            )
            if not result.get("success"):
                return {"success": False, "error": f"Kullanıcı doğrulama hatası: {result.get('error', 'bilinmeyen')}"}
            authenticated_id = result.get("data")
        else:
            authenticated_id = user_id_or_tc

        if not authenticated_id:
            return {"success": False, "error": "Kimlik doğrulama başarısız: user_id bulunamadı."}
    except Exception as auth_err:
        return {"success": False, "error": f"Kimlik doğrulama hatası: {auth_err}"}

    try:
        CURRENT_CONTEXT["user_id"] = authenticated_id
        memory.set_context(authenticated_id, "current_task", "giris")
    except Exception as mem_err:
        pass

    try:
        decision = run_supervisor(message)
        if decision.get("decision") == "ContextSwitch" and decision.get("detected_new_intent"):
            memory.set_context(authenticated_id, "suspended_task", memory.get_context(authenticated_id, "current_task"))
            memory.set_context(authenticated_id, "current_task", decision["detected_new_intent"])
    except Exception:
        pass

    try:
        agent = build_agent(prefix_extra=SYSTEM_PROMPT_TR)

        llm_input = f"[user_id:{authenticated_id}] {message}"

        result = agent.invoke({"input": llm_input})
        raw = result["output"] if isinstance(result, dict) and "output" in result else result

        raw = _strip_think(raw)
        cleaned = sanitize_llm_text(raw) if 'sanitize_llm_text' in globals() else raw
        response_text = (cleaned or raw or "").strip()

        if not response_text:
            response_text = "Üzgünüm, şu an yanıt üretemedim."

        return {"success": True, "response": response_text}

    except Exception as e:
        return {"success": False, "error": f"Agent hatası: {str(e)}"}

# --- MAIN ENTRY --------------------------------------------------------------
if __name__ == "__main__":
    print("Çağrı merkezi ajanına hoş geldiniz. Nasıl yardımcı olabilirim?\n")
    context = {"user_id": None}
    CURRENT_CONTEXT.update(context)

    while not context["user_id"]:
        print("\n[Ajan]: Merhaba, lütfen TC kimlik numaranızı giriniz.")
        tc_input = input("TC Kimlik No: ").strip()

        if not is_valid_tc_format(tc_input):
            print("[Uyarı]: Geçersiz TC Kimlik numarası.")
            continue

        result = get_user_id_from_tc_and_verify_identity(tc=tc_input, challenge_response=tc_input)
        if result["success"]:
            context["user_id"] = result["data"]
            memory.set_context(context["user_id"], "current_task", "giris")
            print("[Sistem]: Giriş başarılı.")
        else:
            print(f"[Hata]: {result['error']}")

    while True:
        soru = input("Soru: ").strip()
        if soru.lower() in ["q", "quit", "exit", "çık", "çıkış"]:
            print("Sistemden çıkılıyor...")
            break

        soru_tagged = f"[user_id:{context['user_id']}] {soru}" if context.get("user_id") else soru
        decision = run_supervisor(soru)
        uid = context["user_id"]

        if decision["decision"] == "ContextSwitch" and decision.get("detected_new_intent"):
            memory.set_context(uid, "suspended_task", memory.get_context(uid, "current_task"))
            memory.set_context(uid, "current_task", decision["detected_new_intent"])

        if context.get("user_id"):
            soru = f"[user_id:{context['user_id']}] {soru}"

        agent = build_agent(prefix_extra=SYSTEM_PROMPT_TR)
        raw = agent.run(soru)
        cevap = sanitize_llm_text(raw)
        print(f"Cevap: {cevap}\n")