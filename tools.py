import datetime
import uuid
from memory import AgentMemory
from typing import Optional, List, Dict, Any
from langchain.tools import StructuredTool
import uuid
from mock_apis import add_user_to_campaign

from mock_apis import (
    get_mock_verify,
    get_mock_campaigns,
    get_mock_service_requests,
    c_support_ticket,
    save_mock_user,
    create_mock_feedback,
    create_mock_package_request,
    get_mock_user,
    get_mock_available_packages,
    get_mock_additional_packages,
    get_mock_bills,
    # mock_bills,
    create_mock_billing_dispute,
    get_mock_packages,
    change_mock_user_package,
    get_user_bills,
    get_connection,
    get_user_id_from_tc,
    get_cancel_current_package
    # get_package_information,
    # get_user_info,
    # get_available_packages,
    # initiate_package_change,
    # cancel_current_package,
    # get_bill_info
)

memory = AgentMemory()

def general_question(
    message: str = "",
    context: dict = None,
    chat_history: list = None,
    memory: AgentMemory = None,
    tool_chain: list = None,
    parameters: dict = None
):
    from agent_runner import run_dialogue_step
    from tool_registry import tool_registry
    """
    LLM tool'ları eşleştiremezse devreye giren fallback.
    - if/elif akışı korunmuştur.
    - execute_tool_chain kullanılmadan tool fonksiyonları doğrudan çağrılır.
    - tool_chain: ["join_campaign", "pay_bill", ...] gibi isim listesi
    - parameters: mevcut ortak param havuzu (user_id dahil)
    """
    context = context or {}
    chat_history = chat_history or []
    parameters = parameters or {}
    user_id = context.get("user_id")

    # Yardımcılar
    def _get_tool_entry(name: str):
        return next((t for t in tool_registry if t["name"] == name), None)

    def _call_tool(name: str, call_args: dict):
        entry = _get_tool_entry(name)
        if not entry:
            return {"success": False, "message": f"[Araç Hatası - {name}] Kayıtlı değil."}
        func = entry["function"]
        try:
            return func(**call_args)
        except Exception as e:
            return {"success": False, "message": f"[Araç Hatası - {name}] {e}"}

    def _required_params(name: str):
        entry = _get_tool_entry(name)
        return entry.get("params", []) if entry else []

    if not tool_chain:
        # Herhangi bir tool yoksa, kibar bir netleştirme mesajı dön ve çık.
        reply = "Sorunuzu toollarla eşleştiremedim. Ne yapmak istediğinizi biraz daha net yazabilir misiniz?"
        memory.add_interaction(user_id, "agent", reply, type="fallback", metadata={"reason": "empty_tool_chain"})
        return {
            "intent": "general_question_fallback",
            "parameters": parameters,
            "tool_chain": [],
            "missing_parameters": [],
            "tool_results": [],
            "raw": None,
            "reply": reply
        }

    tool_results = []
    all_ok = True

    for tool in tool_chain:
        # Her tool için ortak param havuzundan gerekli paramları derle
        reqs = _required_params(tool)
        call_args = {}

        # Eksikleri input() ile topla (mevcut akışını koruyarak)
        for p in reqs:
            if p in parameters and parameters[p] not in (None, ""):
                call_args[p] = parameters[p]
                continue

            # Parametreye özel basit tip dönüşümleri (senin akışınla uyumlu)
            if tool == "pay_bill" and p == "amount":
                while True:
                    try:
                        val = float(input("Lütfen ödemek istediğiniz fatura tutarını giriniz (TL): ").strip())
                        call_args[p] = val
                        parameters[p] = val
                        break
                    except ValueError:
                        print("Geçerli bir sayı giriniz.")
                continue

            if tool == "request_additional_package" and p == "quantity":
                while True:
                    try:
                        val = int(input("Lütfen talep edilen paket adedini giriniz: ").strip())
                        call_args[p] = val
                        parameters[p] = val
                        break
                    except ValueError:
                        print("Geçerli bir sayı giriniz.")
                continue

            # Genel prompt
            prompt_map = {
                "campaign_id": "Lütfen katılmak istediğiniz kampanya ID'sini giriniz: ",
                "service_type": "Lütfen hizmet türünü giriniz (ör: internet, sms, telefon): ",
                "description": "Lütfen sorununuzu veya talebinizi açıklayınız: ",
                "ticket_id": "Lütfen destek talebi ID'sini giriniz: ",
                "method": "Lütfen ödeme yöntemini giriniz (Kredi Kartı, Havale, Mobil Ödeme): ",
                "package_name": "Lütfen paket adını giriniz: ",
                "reason": "Lütfen fatura itirazınızı giriniz: ",
                "package_type": "Lütfen ek paket türünü giriniz (örn. internet, sms, dakika, her şey dahil): ",
                "package_id": "Lütfen yeni paket ID'sini giriniz: ",
                "feedback_text": "Lütfen geri bildiriminizi yazınız (en az 10 karakter): ",
                "rating": "Lütfen 1-5 arası bir puan veriniz (boş bırakabilirsiniz): ",
                "month": "Hangi aya ait fatura bilgisini öğrenmek istiyorsunuz? ",
                "user_id": "Lütfen kullanıcı ID'sini giriniz: ",
            }
            val = input(prompt_map.get(p, f"Lütfen '{p}' bilgisini giriniz: ")).strip()
            if p == "rating" and val:
                try:
                    val = int(val)
                except ValueError:
                    print("Geçerli bir sayı giriniz veya boş bırakınız.")
                    val = None

            call_args[p] = val
            parameters[p] = val

        # Doğrudan tool'u çağır
        result = _call_tool(tool, call_args)
        tool_results.append(result)
        memory.add_interaction(user_id, "agent", result, type="tool", metadata={"tool": tool})

        # Başarı kontrolü (dict success öncelik; değilse string hata yakala)
        ok = True
        if isinstance(result, dict):
            ok = (result.get("success") is True)
        elif isinstance(result, str):
            ok = not result.startswith(f"[Araç Hatası - {tool}]")

        if not ok:
            all_ok = False
            # Hatalı parametreleri yeniden sorulabilir kılmak üzere bazılarını temizle
            if tool == "pay_bill":
                parameters["amount"] = None
                parameters["method"] = ""
            if tool in ("join_campaign", "get_package_id_by_name"):
                parameters.setdefault("campaign_id", "")
                parameters.setdefault("package_name", "")
            if tool in ("get_ticket_status", "cancel_support_ticket"):
                parameters["ticket_id"] = ""
            if tool == "request_additional_package":
                parameters["package_type"] = ""
                parameters["package_name"] = ""
                parameters["quantity"] = None
            if tool == "submit_feedback":
                parameters["feedback_text"] = ""
                parameters["rating"] = None
            if tool == "get_bill_info":
                parameters["month"] = ""

            # Bu noktada sen istersen while döngüsüyle yeniden denettirebilirsin.
            # (Mevcut yapın gibi tekrar sormak için burada continue ile yeni input döngüsü açılabilir.)

        else:
            memory.set_last_successful_action(user_id, tool)

    # Zincir sonucu
    if all_ok:
        memory.set_last_successful_action(user_id, "tool_chain_completed")
        reply = "İşlemler başarıyla tamamlandı."
    else:
        reply = "Bazı işlemler tamamlanamadı. Eksik/hatalı bilgiler olabilir; tekrar deneyebilirsiniz."

    return {
        "intent": "general_question_fallback",
        "parameters": parameters,
        "tool_chain": tool_chain,
        "missing_parameters": [],
        "tool_results": tool_results,
        "raw": None,
        "reply": reply
    }


def get_campaigns(user_id: str):
    """
    Kullanıcının katılabileceği güncel kampanyaları listeler.
    """

    campaigns = get_mock_campaigns(user_id)
    today = datetime.datetime.today().date()

    # Geçerlilik tarihi geçmiş olan kampanyalar filtrelenir
    active_campaigns = [
        campaign for campaign in campaigns
        if datetime.datetime.strptime(campaign["valid_until"], "%Y-%m-%d").date() >= today
    ]

    if not active_campaigns:
        return {"success": False, "error": "Mevcut kampanya bulunmamaktadır."}

    return {"success": True, "data": active_campaigns}

def join_campaign(user_id: str, campaign_id: str):
    """
    Kullanıcının bir kampanyaya katılma işlemi yapılır.
    """
    campaigns = get_mock_campaigns(user_id)
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)

    if not campaign:
        return {"success": False, "error": f"{campaign_id} id'sine sahip kampanya bulunamadı."}

    # Kampanya süresi kontrolü
    valid_until = datetime.datetime.strptime(campaign["valid_until"], "%Y-%m-%d").date()
    if valid_until < datetime.datetime.today().date():
        return {"success": False, "error": "Kampanyanın süresi dolmuş."}

    # Kullanıcının daha önce katılıp katılmadığı kontrolü
    if "joined_users" in campaign and user_id in campaign["joined_users"]:
        return {"success": False, "error": "Bu kampanyaya zaten katıldınız."}

    add_user_to_campaign(user_id, campaign_id)
 
    return {"success": True, "message": "Kampanyaya başarıyla katıldınız.", "campaign": campaign}

def get_user_id_from_tc_and_verify_identity(tc: str, challenge_response: str):
    """
    Kullanıcının TC kimlik numarasına göre user_id'yi döner ve kimlik doğrulamasını yapar.
    """

    user_id = get_user_id_from_tc(tc=tc)

    if not user_id:
        return {"success": False, "error": "Kullanıcı bulunamadı."}

    user = get_mock_verify(user_id)

    if user and user.get("tc") == challenge_response:
        return {"success": True, "data": user_id, "message": "Kimlik doğrulaması başarılı."}

    return {"success": False, "error": "Kimlik doğrulama başarısız."}

# Bu değişken ile kayıt sırasında eksik alanları tutuyoruz
user_registration_state: Dict[str, Dict[str, Any]] = {}


def register_user(tc: Optional[str] = None, name: Optional[str] = None, email: Optional[str] = None, package: Optional[str] = None, package_id: Optional[str] = None, line_status: Optional[str] = None, session_id: Optional[str] = None):

    # Session yoksa başlat
    if not session_id:
        session_id = str(uuid.uuid4())
        user_registration_state[session_id] = {
            "tc": None,
            "name": None,
            "email": None,
            "package": None,
            "package_id": None,
            "line_status": None
        }

    # Gelen verileri state'e yaz
    for key, value in {"tc": tc, "name": name, "email": email,
                       "package": package, "package_id": package_id, "line_status": line_status}.items():
        if value:
            user_registration_state[session_id][key] = value

    # Eksik alan kontrolü
    for field in ["tc", "name", "email", "package", "package_id", "line_status"]:
        if not user_registration_state[session_id][field]:
            return {
                "success": False,
                "session_id": session_id,
                "message": f"Lütfen {field} bilgisini giriniz."
            }

    # Tüm alanlar doldu → kayıt yap
    save_mock_user({
        "user_id": session_id,
        **user_registration_state[session_id]
    })
    del user_registration_state[session_id]

    return {
        "success": True,
        "message": "Kayıt başarılı.",
        "session_id": session_id
    }


def create_support_ticket(user_id, service_type, description):
    """
    Belirtilen servis türü için yeni bir teknik destek talebi oluşturur.
    Eğer kullanıcı aynı servis için aktif bir talep oluşturmuşsa tekrar oluşturulmaz.
    """
    user = get_mock_verify(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}
    
    existing_requests = get_mock_service_requests(user_id)
    if existing_requests.get("success") and existing_requests.get("data"):
        for request in existing_requests["data"]:
            if request["service_type"] == service_type and request["status"] in ["Talep alındı", "İşlemde"]:
                return {
                    "success": False,
                    "error": f"{service_type} servisi için zaten aktif bir talebiniz bulunmaktadır."
                }

    result = c_support_ticket(user_id, service_type, description)
    if result["success"]:
        return {
            "success": True,
            "ticket_id": result["ticket_id"],
            "message": result["message"]
        }
    else:
        return {
            "success": False,
            "error": f"Talep oluşturulamadı: {result['error']}"
        }

def get_ticket_status(user_id, ticket_id):
    """
    Belirli bir destek talebinin güncel durumunu getirir.
    """
    tickets_response = get_mock_service_requests(user_id)
    
    if not tickets_response.get("success"):
        return {"success": False, "error": "Destek talepleri alınamadı."}
    
    tickets = tickets_response["data"]
    ticket = next((t for t in tickets if t["ticket_id"] == ticket_id), None)

    if ticket:
        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": ticket["status"],
            "service_type": ticket["service_type"],
            "description": ticket["description"],}
    else:
        return {"success": False, "error": "Destek talebi bulunamadı."}
    
def cancel_support_ticket(user_id, ticket_id):
    """
    Belirtilen destek talebinin durumunu 'İptal edildi' olarak günceller.
    Talep gerçekten o kullanıcıya aitse iptal edilir.
    """
    tickets_response = get_mock_service_requests(user_id)

    if not tickets_response.get("success"):
        return {"success": False, "error": "Destek talepleri alınamadı."}

    tickets = tickets_response["data"]

    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            if ticket["status"] in ["Tamamlandı", "İptal edildi"]:
                return {"success": False, "error": f"{ticket_id} numaralı destek talebi zaten {ticket['status'].lower()}."}

            ticket["status"] = "İptal edildi"
            ticket["cancelled_at"] = datetime.datetime.now().isoformat()
            return {
                "success": True,
                "message": f"{ticket_id} numaralı destek talebiniz iptal edilmiştir.",
                "status": ticket["status"]
            }

    return {"success": False, "error": "İptal edilecek destek talebi bulunamadı."}



def get_outstanding_balance(user_id: str) -> dict:
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}
    bills = get_user_bills(user_id)
    if not bills:
        return {"success": False, "error": "Fatura bulunamadı."}

    # Veritabanında "ödenmedi" veya "beklemede" olarak tutulan faturalar
    relevant_statuses = ["ödenmedi", "beklemede"]

    unpaid_total = sum(
        bill["amount"] 
        for bill in bills 
        if bill["status"].lower() in relevant_statuses)
    if unpaid_total == 0:
        return {"success": False, "error": "Tüm faturalar ödenmiş durumda."}

    return {
         "success": True,
         "data": f"Toplam ödenmemiş/beklemede fatura borcunuz: {unpaid_total:.2f} TL"}


def pay_bill(user_id: str, amount: float, method: str) -> dict:
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    valid_methods = ['kredi kartı', 'havale', 'mobil ödeme']
    method = method.lower()
    if method not in valid_methods:
        return {
            "success": False,
            "error": f"Geçersiz ödeme yöntemi. Geçerli yöntemler: {', '.join(valid_methods)}"
        }

    if amount <= 0:
        return {"success": False, "error": "Geçersiz ödeme miktarı."}

    conn = get_connection()
    cur = conn.cursor()

    # Fatura ile birebir eşleşen ve ödenmemiş bir fatura ara
    cur.execute("""
        SELECT bill_id, due_date FROM bills 
        WHERE user_id = ? AND status = 'unpaid' AND ABS(amount - ?) < 0.01
        LIMIT 1
    """, (user_id, amount))
    row = cur.fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": f"{amount:.2f} TL tutarında ödenecek fatura bulunamadı."}

    bill_id, due_date = row

    # Ödeme işlemini yap (status = paid)
    cur.execute("""
        UPDATE bills SET status = 'paid' WHERE bill_id = ?
    """, (bill_id,))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": (
            f"{user['name']} adlı kullanıcı, {due_date} tarihli "
            f"{amount:.2f} TL tutarındaki faturasını '{method}' ile başarıyla ödedi."
        )
    }


def get_line_status(user_id: str) -> dict:
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    line_status = user.get("line_status")
    if not line_status:
        return {"success": False, "error": "Kullanıcıya ait hat durumu bilgisi bulunamadı."}

    valid_statuses = {"faturalı", "faturasız", "askıda", "iptal"}
    if line_status not in valid_statuses:
        return {"success": False, "error": f"Bilinmeyen hat durumu: '{line_status}'."}

    return {
        "success": True,
        "data": f"Hattınızın mevcut durumu: {line_status}."
    }



def get_package_id_by_name(user_id: str, package_name: str) -> dict:
    """
    Kullanıcının erişebileceği paketler arasında verilen ada göre paket ID'sini döndürür.
    """
    packages = get_mock_available_packages(user_id)
    package_name = package_name.strip()

    for pkg in packages:
        if pkg["name"].lower() == package_name.lower():
            return {
                "success": True,
                "package_id": pkg["package_id"],
                "data": f"{pkg['name']} paketi bulundu. Paket ID: {pkg['package_id']}"
            }

    return {
        "success": False,
        "error": f"'{package_name}' adına sahip bir paket bulunamadı."
    }


def initiate_billing_dispute(user_id: str, reason: str) -> dict:
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    if not reason or len(reason.strip()) < 6:
        return {"success": False, "error": "Lütfen itiraz sebebini en az 6 karakter olarak belirtin."}

    result = create_mock_billing_dispute(user_id, reason)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Fatura itirazı oluşturulamadı. Lütfen tekrar deneyin.")}

    return {
        "success": True,
        "message": result.get("message"),
        "dispute_info": {
            "user_id": user_id,
            "user_name": user["name"],
            "reason": reason
        }
    
    }

# Hafıza alanı (oturum bazlı saklama için global değişken yerine session memory kullanabilirsin)
last_package_request = {}

def _norm(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

def _lower(s: str) -> str:
    return s.strip().lower() if isinstance(s, str) else s

def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        k = _lower(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


# --- Asıl Tool ---
def request_additional_package(
    user_id: str,
    package_type: Optional[str] = None,
    package_name: Optional[str] = None,
    quantity: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Eksik alanları sırayla tamamlar; hafızaya yazar ve son adımda DB’ye kaydeder.
    - package_type verilmemişse package_name'den otomatik çıkarır (mümkünse)
    - Kullanıcı yalnızca '3' gibi miktar gönderirse, önceki seçimlerle birleştirir
    """

    # 0) Önceki adımları tamamla (hafıza)
    prev = last_package_request.get(user_id, {})
    package_type = package_type or prev.get("package_type")
    package_name = package_name or prev.get("package_name")
    quantity     = quantity     if quantity not in (None, 0) else prev.get("quantity")
    start_date   = start_date   or prev.get("start_date")
    end_date     = end_date     or prev.get("end_date")

    # 1) Kullanıcı kontrolü
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    # 2) Türü otomatik belirlemeye çalış (paket adı varsa)
    if not package_type and package_name:
        package_type = infer_package_type_from_name(package_name)

    # 3) Tür hâlâ yoksa kullanıcıdan iste
    if not package_type:
        # Hafızaya güncel durumu yaz
        last_package_request[user_id] = {
            "package_type": None,
            "package_name": package_name,
            "quantity": quantity,
            "start_date": start_date,
            "end_date": end_date,
        }
        return {
            "success": False,
            "ask_user": True,
            "question": "Hangi tür ek paket almak istersiniz? (internet / sms / dakika / her şey dahil)",
            "missing_field": "package_type",
        }

    package_type = _lower(package_type)

    # 4) Tür için uygun paketleri getir
    # get_mock_additional_packages(user_id, package_type) şeklinde tür filtresi varsa onu kullan.
    try:
        add_pkgs = get_mock_additional_packages(user_id, package_type)
    except TypeError:
        # Sende ikinci parametre yoksa fallback: tümünü al, sonra filtrele
        all_pkgs = get_mock_additional_packages(user_id)
        add_pkgs = [p for p in (all_pkgs or []) if _lower(p.get("package_type")) == package_type]

    if not add_pkgs:
        return {"success": False, "error": f"'{package_type}' türünde ek paket bulunamadı."}

    # 5) Paket adı yoksa seçenekleri listele
    if not package_name:
        options = _dedupe_keep_order([p["package_name"] for p in add_pkgs])
        last_package_request[user_id] = {
            "package_type": package_type,
            "package_name": None,
            "quantity": quantity,
            "start_date": start_date,
            "end_date": end_date,
        }
        return {
            "success": False,
            "ask_user": True,
            "question": f"{package_type} türünde mevcut paketler: {', '.join(options)}. Hangisini almak istersiniz?",
            "missing_field": "package_name",
            "available_options": options,
        }

    # 6) Verilen paket adı geçerli mi? (case-insensitive)
    package_name_norm = _lower(package_name)
    valid_names_norm = {_lower(p["package_name"]): p["package_name"] for p in add_pkgs}
    if package_name_norm not in valid_names_norm:
        options = _dedupe_keep_order([p["package_name"] for p in add_pkgs])
        # Hafızayı güncelle
        last_package_request[user_id] = {
            "package_type": package_type,
            "package_name": None,  # yanlış isim geldi; tekrar istiyoruz
            "quantity": quantity,
            "start_date": start_date,
            "end_date": end_date,
        }
        return {
            "success": False,
            "ask_user": True,
            "question": f"'{package_name}' bulunamadı. {package_type} türünde seçenekler: {', '.join(options)}. Hangisini almak istersiniz?",
            "missing_field": "package_name",
            "available_options": options,
        }

    # Orijinal isimle devam edelim (format korunsun)
    package_name = valid_names_norm[package_name_norm]

    # 7) Miktar yoksa sor
    if quantity is None or quantity <= 0:
        last_package_request[user_id] = {
            "package_type": package_type,
            "package_name": package_name,
            "quantity": None,
            "start_date": start_date,
            "end_date": end_date,
        }
        return {
            "success": False,
            "ask_user": True,
            "question": f"Kaç adet {package_name} almak istersiniz? (sayı olarak)",
            "missing_field": "quantity",
        }

    # 8) DB kayıt (SQLite için örnek create fonksiyonu aşağıda)
    result = create_mock_package_request(
        user_id=user_id,
        package_type=_norm(package_type),
        package_name=_norm(package_name),
        quantity=quantity,
        start_date=_norm(start_date),
        end_date=_norm(end_date),
    )

    if not result.get("success"):
        # Hata varsa hafızayı silmemek daha iyi; kullanıcı düzeltme yapabilir
        return {"success": False, "error": result.get("error", "Ek paket talebi oluşturulamadı.")}

    # 9) Başarılı → hafızayı temizle
    last_package_request.pop(user_id, None)

    return {
        "success": True,
        "message": f"{package_name} paketinden {quantity} adet talebiniz başarıyla alındı.",
        "request_info": {
            "user_id": user_id,
            "user_name": user.get("name"),
            "package_type": package_type,
            "package_name": package_name,
            "quantity": quantity,
            "start_date": start_date,
            "end_date": end_date,
        },
    }


# (İsteğe bağlı) Hafızayı manuel temizlemek istersen:
def reset_last_package_request(user_id: str):
    last_package_request.pop(user_id, None)



def infer_package_type_from_name(package_name: str) -> str:
    """Paket adından paket türünü tahmin eder."""
    if not package_name:
        return None

    name = package_name.lower()

    if "gb" in name or "internet" in name:
        return "internet"
    elif "sms" in name:
        return "sms"
    elif "dakika" in name or "dk" in name:
        return "dakika"

    elif "her şey dahil" in package_name or "paket" in package_name:
        return "her şey dahil"
    else:
        return None



def submit_feedback(user_id: str, feedback_text: str, rating: int = None) -> dict:
    """
    Kullanıcının sistemle veya paketlerle ilgili geri bildirimini alır.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        return {"success": False, "error": "Geçersiz kullanıcı ID."}

    if not isinstance(feedback_text, str) or len(feedback_text.strip()) < 10:
        return {"success": False, "error": "Geri bildirim en az 10 karakter olmalıdır."}

    if rating is not None:
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return {"success": False, "error": "Puan 1 ile 5 arasında olmalıdır."}

    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    # mock_apis'e yönlendir
    result = create_mock_feedback(user_id, feedback_text, rating)

    if not result.get("success"):
        return {"success": False, "error": "Geri bildirim kaydı başarısız oldu."}

    return {
        "success": True,
        "message": result["message"],
        "feedback_info": {
            "user_id": user_id,
            "user_name": user["name"],
            "rating": rating,
            "feedback_text": feedback_text.strip()
        }
    }


def get_available_packages(user_id: str):
    """
    Kullanıcı için tüm paketleri getirir.
    """
    try:
        packages = get_mock_available_packages(user_id)
    except KeyError  as e:
        return {"success": False, "error": f"Paket listesini alırken hata: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Beklenmeyen bir hata oluştu: {e}"}
    if not packages:
        return {"success": False, "error": "Uygun paket bulunamadı."}
    return {"success": True, "data": packages}

def get_additional_packages(user_id: str):
    """
    Kullanıcı için ek paketleri getirir.
    """
    try:
        additional_packages = get_mock_additional_packages(user_id)
    except KeyError  as e:
        return {"success": False, "error": f"Paket listesini alırken hata: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Beklenmeyen bir hata oluştu: {e}"}
    if not additional_packages:
        return {"success": False, "error": "Ek paket bulunamadı."}
    return {"success": True, "data": additional_packages}

def initiate_package_change(user_id: str, package_id: str):
    """
    Paket değişikliğini başlatır.
    """
    print(f"initiate_package_change user_id ile çağrıldı.={user_id}, package_id={package_id}")  # debug
    try:
        available = get_mock_available_packages(user_id)
    except Exception as e:
        return {"success": False, "error": f"Available packages alınamadı: {e}"}

    valid_ids = [pkg.get("package_id") for pkg in available]
    if package_id not in valid_ids:
        print("Invalid package_id")  # debug
        return {"success": False, "error": "Geçersiz paket ID'si seçildi."}

    result = change_mock_user_package(user_id, package_id)
    if not result.get("success", False):
        return result
    print("Result from change_mock_user_package:", result)  # debug

    return {"success": True, "data": result}

def get_user_info(user_id: str):
    """
    Kullanıcının temel bilgilerini döner.
    """
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı {user_id} bulunamadı."}
    return {"success": True, "data": user}

def get_package_information(user_id: str):
    """
    Kullanıcının paket bilgisini döner.
    """
    user = get_mock_user(user_id)
    if not user:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}
    
    package_name = user.get("package")
    package_details = get_mock_packages(package_name)

    if not package_details:
        return {"success": False, "error": f"Paket detayları '{package_name}' için bulunamadı."}
    return {"success": True, "data": f"Mevcut paketiniz: '{package_name}' "}

def cancel_current_package(user_id: str) -> dict:
    """
    Mevcut paketi iptal eder.
    """
    result = get_cancel_current_package(user_id)  
    
    if not result.get("success"):
        return result  

    return { "success": True, "data": result.get("message"), "status": result.get("status") }


def get_bill_info(user_id: str, month: str) -> dict:
    """
    Kullanıcının o aya ait fatura bilgisini alır.
    """
    # Önce ay bilgisi var mı kontrol et
    if not month:
        return {
            "success": False,
            "ask_user": True,
            "question": "Hangi aydaki fatura bilginizi öğrenmek istersiniz? (YYYY-AA şeklinde giriniz lütfen)",
            "missing_field": "month"
        }

    user = get_mock_user(user_id)
    bills = get_mock_bills(user_id)
    amount = bills.get(month)
    
    # Kullanıcı hiç yok ve faturası da yoksa
    if not user and not bills:
        return {"success": False, "error": f"Kullanıcı '{user_id}' bulunamadı."}

    # İlgili ayın faturası yoksa
    if amount is None:
        return {"success": False, "error": f"{month} ayı için fatura bilgisi bulunamadı."}

    return {
        "success": True,
        "data": f"{month} ayına ait fatura tutarınız: {amount:.2f} TL"
    }