import datetime
import sqlite3
import uuid

DB_PATH = "alfai.db"

def get_connection():
    return sqlite3.connect(DB_PATH)


def get_cancel_current_package(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Kullanıcıyı kontrol et
    cur.execute("SELECT package, package_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Paket bilgisi bulunamadı."}

    package, package_id = row
    if not package and not package_id:
        conn.close()
        return {"success": False, "error": "Zaten aktif paketiniz bulunmuyor."}

    try:
        # package ve package_id alanlarını NULL yap
        cur.execute("""
            UPDATE users
            SET package = NULL, package_id = NULL
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()

        return {
            "success": True,
            "message": f"{user_id} numaralı kullanıcının mevcut paketi iptal edilmiştir.",
            "status": "Paket iptal edildi"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_mock_verify(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, tc, name, email FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "tc": row[1], "name": row[2], "email": row[3]}
    return None

def get_user_id_from_tc(tc):
    """
    Verilen T.C. kimlik numarasına karşılık gelen user_id'yi döner.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE tc = ?", (tc,))
    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]  # user_id
    return None

def add_user_to_campaign(user_id, campaign_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Kullanıcının kampanyaya zaten katılıp katılmadığını kontrol et
        cur.execute("SELECT 1 FROM users_campaigns WHERE user_id = ? AND campaign_id = ?", (user_id, campaign_id))
        if cur.fetchone():
            return {"success": False, "error": "Bu kampanyaya zaten katıldınız."}

        # Kampanya geçerlilik kontrolü (opsiyonel, tools'da da yapılabilir)
        cur.execute("SELECT valid_until FROM campaigns WHERE id = ?", (campaign_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "Kampanya bulunamadı."}
        valid_until = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
        if valid_until < datetime.date.today():
            return {"success": False, "error": "Kampanyanın süresi dolmuş."}

        # Katılım kaydını yap
        cur.execute("INSERT INTO users_campaigns (user_id, campaign_id) VALUES (?, ?)", (user_id, campaign_id))
        conn.commit()
        return {"success": True, "message": "Kampanyaya başarıyla katıldınız."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def get_mock_campaigns(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Öncelikle kullanıcının katıldığı kampanyaların id'lerini alalım
    cur.execute("SELECT campaign_id FROM users_campaigns WHERE user_id = ?", (user_id,))
    joined_campaign_ids = {row[0] for row in cur.fetchall()}

    # Kampanyaları al, sadece katılmadığı kampanyalar gelsin (istersen katıldıkları ayrı fonksiyonda alınabilir)
    cur.execute("""
        SELECT id, title, description, valid_until 
        FROM campaigns 
        WHERE (user_id = ? and user_id = 'default')
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    campaigns = []
    for row in rows:
        campaign_id = row[0]
        if campaign_id not in joined_campaign_ids:
            campaigns.append({
                "id": campaign_id,
                "title": row[1],
                "description": row[2],
                "valid_until": row[3]
            })

    return campaigns

def get_user_joined_campaigns(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.title, c.description, c.valid_until 
        FROM campaigns c
        JOIN users_campaigns uc ON c.id = uc.campaign_id
        WHERE uc.user_id = ?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    return [
        {"id": r[0], "title": r[1], "description": r[2], "valid_until": r[3]} for r in rows
    ]

def get_mock_service_requests(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ticket_id, service_type, description, status, created_at, cancelled_at
        FROM support_tickets WHERE user_id = ?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {"success": False, "error": "Destek talepleri bulunamadı."}

    data = []
    for r in rows:
        data.append({
            "ticket_id": r[0],
            "service_type": r[1],
            "description": r[2],
            "status": r[3],
            "created_at": r[4],
            "cancelled_at": r[5]
        })
    return {"success": True, "data": data}

def c_support_ticket(user_id, service_type, description):
    conn = get_connection()
    cur = conn.cursor()

    ticket_id = f"TCK{int(datetime.datetime.now().timestamp())}{uuid.uuid4().hex[:6]}"
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur.execute("""
            INSERT INTO support_tickets (ticket_id, user_id, service_type, description, status, created_at, cancelled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, user_id, service_type, description, "Talep alındı", created_at, None))

        conn.commit()
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"{service_type} ile ilgili destek talebiniz oluşturuldu.",
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "ticket_id": None,
            "message": None,
            "error": str(e)
        }
    finally:
        conn.close()

def get_cancel_support_ticket(user_id, ticket_id):
    conn = get_connection()
    cur = conn.cursor()

    # Talebi sorgula
    cur.execute("SELECT status FROM support_tickets WHERE user_id = ? AND ticket_id = ?", (user_id, ticket_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "İptal edilecek destek talebi bulunamadı."}

    status = row[0]
    if status in ["Tamamlandı", "İptal edildi"]:
        conn.close()
        return {"success": False, "error": f"{ticket_id} numaralı destek talebi zaten {status.lower()}."}

    # Durumu güncelle
    cancelled_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur.execute("""
            UPDATE support_tickets SET status = ?, cancelled_at = ? WHERE user_id = ? AND ticket_id = ?
        """, ("İptal edildi", cancelled_at, user_id, ticket_id))
        conn.commit()
        return {
            "success": True,
            "message": f"{ticket_id} numaralı destek talebiniz iptal edilmiştir.",
            "status": "İptal edildi"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def save_mock_user(user_data):
    """
    user_data = {
        "user_id": str,
        "tc": str,
        "name": str,
        "email": str
    }
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # TC unique kontrolü
        cur.execute("SELECT user_id FROM users WHERE tc = ?", (user_data["tc"],))
        if cur.fetchone():
            return {"success": False, "error": "Bu TC kimlik numarası zaten kayıtlı."}

        cur.execute("""
            INSERT INTO users (user_id, tc, name, email)
            VALUES (?, ?, ?, ?)
        """, (user_data["user_id"], user_data["tc"], user_data["name"], user_data["email"]))
        conn.commit()
        return {"success": True, "message": "Kullanıcı başarıyla kaydedildi."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def get_mock_user(user_id: str) -> dict:
    """Kullanıcı bilgilerini döner veya None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, tc, name, email, package, package_id, line_status FROM users WHERE user_id = ?", (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "tc": row[1],
            "name": row[2],
            "email": row[3],
            "package": row[4],
            "package_id": row[5],
            "line_status": row[6]
        }
    return None


def get_mock_available_packages(user_id: str) -> list:
    """Tüm paketleri listeler."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT package_id, name, price, details, data_cap_gb FROM packages"
    )
    rows = cur.fetchall()
    conn.close()
    packages = []
    for pid, name, price, details, cap in rows:
        packages.append({
            "package_id": pid,
            "name": name,
            "price": price,
            "details": details,
            "data_cap_gb": cap
        })
    return packages



def get_mock_additional_packages(user_id: str, package_type: str = None) -> list:
    """Tüm ek paketleri listeler."""
    conn = get_connection()
    cur = conn.cursor()

    try:
        if package_type:
            cur.execute("""
                SELECT package_name, package_type FROM package_requests WHERE package_type = ? """, (package_type,))
        else:
            cur.execute(""" SELECT package_name, package_type FROM package_requests """)

        rows = cur.fetchall()
        packages = [
            {"package_name": r[0], "package_type": r[1]}
            for r in rows
        ]
        return packages
    finally:
        conn.close()



def change_mock_user_package(user_id: str, package_id: str) -> dict:
    """Kullanıcının paketini günceller."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Paket var mı?
        cur.execute(
            "SELECT name FROM packages WHERE package_id = ?", (package_id,)
        )
        pkg = cur.fetchone()
        if not pkg:
            return {"success": False, "error": "Paket bulunamadı."}
        # Güncelle
        cur.execute(
            "UPDATE users SET package = ?, package_id = ? WHERE user_id = ?",
            (pkg[0], package_id, user_id)
        )
        conn.commit()
        return {"success": True, "message": f"{pkg[0]} paketine geçiş işleminiz alınmıştır. 24 saat içinde aktifleşecektir."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_mock_bills(user_id: str) -> dict:
    """Kullanıcının faturalarını dict olarak döner."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT month, amount FROM bills WHERE user_id = ?", (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return {month: amt for month, amt in rows}


def get_mock_packages(id_or_name: str) -> dict:
    """Paket ID veya isimle detay getirir."""
    conn = get_connection()
    cur = conn.cursor()
    # ID ile arama
    cur.execute(
        "SELECT package_id, name, price, details, data_cap_gb FROM packages WHERE package_id = ?", (id_or_name,)
    )
    row = cur.fetchone()
    if row:
        conn.close()
        return {"package_id": row[0], "name": row[1], "price": row[2], "details": row[3], "data_cap_gb": row[4]}
    # İsim ile arama
    cur.execute(
        "SELECT package_id, name, price, details, data_cap_gb FROM packages WHERE name = ?", (id_or_name,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"package_id": row[0], "name": row[1], "price": row[2], "details": row[3], "data_cap_gb": row[4]}
    return None

def get_user_bills(user_id: str) -> list:
    """
    Kullanıcının tüm fatura kayıtlarını getirir.

    Returns:
        list of dict: Fatura verileri
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT bill_id, amount, status, due_date
        FROM bills
        WHERE user_id = ?
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    bills = []
    for row in rows:
        bills.append({
            "bill_id": row[0],
            "amount": row[1],
            "status": row[2],
            "due_date": row[3]
        })

    return bills



def create_mock_package_request(user_id: str, package_type: str, package_name: str, start_date: str = None, end_date: str = None, quantity: int = 1) -> dict:
    """
    Ek paket talebini veritabanına kaydeder.

    Args:
        user_id (str): Kullanıcı ID'si
        package_type (str): Paket türü (örn. "internet")
        package_name (str): Paket adı
        quantity (int): Talep adedi

    Returns:
        dict: İşlem sonucu
    """
    from datetime import datetime

    # 1. Kullanıcı kontrolü
    if not get_mock_user(user_id):
        return {"success": False, "error": "Kullanıcı bulunamadı."}

    normalized_type = normalize_package_type(package_type)

    if normalized_type not in VALID_PACKAGE_TYPES:
        return {
            "success": False,
            "error": f"Geçersiz paket türü. Geçerli türler: {', '.join(VALID_PACKAGE_TYPES)}"
        }

    conn = get_connection()
    cur = conn.cursor()

    # 2. Aynı talep daha önce yapılmış mı kontrolü
    cur.execute("""
        SELECT COUNT(*) FROM package_requests
        WHERE user_id = ? AND package_type = ? AND LOWER(package_name) = LOWER(?) AND quantity = ?
    """, (user_id, normalized_type, package_name, quantity))

    if cur.fetchone()[0] > 0:
        conn.close()
        return {"success": False, "error": "Aynı paket talebi zaten yapılmış."}

    # 3. Talep kaydı
    request_id = str(uuid.uuid4())
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "beklemede"

    try:
        cur.execute("""
            INSERT INTO package_requests (
                request_id, user_id, package_type, package_name, quantity, status, created_at, start_date, end_date

            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, user_id, normalized_type, package_name.strip(), quantity, status, created_at, start_date, end_date
        ))

        conn.commit()
        return {
            "success": True,
            "message": "Ek paket talebiniz başarıyla alınmıştır. En kısa sürede değerlendirilecektir.",
            "request": {
                "request_id": request_id,
                "user_id": user_id,
                "package_type": normalized_type,
                "package_name": package_name.strip(),
                "quantity": quantity,
                "status": status,
                "created_at": created_at,
                "start_date": start_date,
                "end_date": end_date
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()



def create_mock_billing_dispute(user_id: str, reason: str) -> dict:
    """
    Kullanıcının fatura itiraz talebini veritabanına kaydeder.

    Args:
        user_id (str): Kullanıcı ID'si
        reason (str): İtiraz nedeni

    Returns:
        dict: Kayıt sonucu
    """
    if not get_mock_user(user_id):
        return {"success": False, "error": "Kullanıcı bulunamadı."}

    if not isinstance(reason, str) or len(reason.strip()) < 5:
        return {"success": False, "error": "Geçerli bir itiraz nedeni giriniz."}

    conn = get_connection()
    cur = conn.cursor()

    dispute_id = str(uuid.uuid4())
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur.execute("""
            INSERT INTO billing_disputes (dispute_id, user_id, reason, created_at)
            VALUES (?, ?, ?, ?)
        """, (dispute_id, user_id, reason.strip(), created_at))

        conn.commit()
        return {
            "success": True,
            "message": "Fatura itiraz talebiniz başarıyla alındı.",
            "dispute": {
                "dispute_id": dispute_id,
                "user_id": user_id,
                "reason": reason.strip(),
                "created_at": created_at
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

VALID_PACKAGE_TYPES = {"internet", "sms", "dakika", "her şey dahil"}

def normalize_package_type(t: str) -> str:
    return t.strip().lower().replace(" ", "")


def create_mock_feedback(user_id, feedback_text, rating=None):
    """
    Kullanıcı geri bildirimini veritabanına kaydeder.

    Args:
        user_id (str): Kullanıcı ID'si
        feedback_text (str): Geri bildirim metni
        rating (int, optional): 1-5 arası puan

    Returns:
        dict: Kayıt sonucu
    """
    conn = get_connection()
    cur = conn.cursor()

    feedback_id = str(uuid.uuid4())
    submitted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur.execute("""
            INSERT INTO feedbacks (feedback_id, user_id, feedback_text, rating, submitted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (feedback_id, user_id, feedback_text.strip(), rating, submitted_at))

        conn.commit()
        return {
            "success": True,
            "message": "Geri bildiriminiz başarıyla kaydedildi.",
            "feedback": {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "feedback_text": feedback_text.strip(),
                "rating": rating,
                "submitted_at": submitted_at
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()