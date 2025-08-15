# lc_tools.py
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr, field_validator
from langchain.tools import StructuredTool
import tools as t 
import re 




# Ortak tipler
PaymentMethod = Literal["kredi kartı", "havale", "mobil ödeme"]
ServiceType   = Literal["internet", "sms", "telefon"]

# YYYY-MM veya Türkçe ay adı destekleyen basit kontrol
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")  # 2025-05 gibi
_TR_MONTHS = {
    "ocak","şubat","mart","nisan","mayıs","haziran",
    "temmuz","ağustos","eylül","ekim","kasım","aralık"
}

# Girdi şemaları: Pydantic BaseModel sınıfları -> Bunlar araçların beklediği parametrelerin tipini ve adlarını tanımlıyor.
# LangChain, bir tool’u çağırmadan önce LLM’in ürettiği argümanları bu şemalara dökmeye çalışır.
# Örn. {"user_id":"123", "campaign_id":"CMP-42"} JSON’u UserIdCampaignId’e parse edilir.
class UserId(BaseModel):
    user_id: str = Field(..., description="Sistemdeki kullanıcı ID'si")

class UserIdMonth(BaseModel):
    user_id: str = Field(..., description="Sistemdeki kullanıcı ID'si")
    month: str = Field(..., description="Ay adı (tr) veya YYYY-MM, ör: 'Mayıs' ya da '2025-05'")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        m = v.strip()
        if _MONTH_RE.match(m):
            return m
        if m.lower() in _TR_MONTHS:
            return m
        raise ValueError("month 'YYYY-MM' veya Türkçe ay adı olmalı (ör. '2025-05' ya da 'Mayıs').")

class UserIdPackageId(BaseModel):
    user_id: str
    package_id: str

class UserIdFeedback(BaseModel):
    user_id: str
    feedback_text: str = Field(..., min_length=10)
    rating: Optional[int] = Field(None, ge=1, le=5)

class UserIdExtraPackage(BaseModel):
    user_id: str
    package_type: Optional[str] = Field(None, description="ör: internet, sms, dakika, her şey dahil")
    package_name: str
    quantity: str = Field("1", description="Kaç adet paket isteniyor (sayı olarak)")

    @field_validator("quantity", mode="before")
    def clean_quantity(cls, v):
        # Metin içinden rakamları al
        if isinstance(v, str):
            import re
            nums = re.findall(r"\d+", v)
            if nums:
                return int(nums[0])
        return int(v)


class UserIdReason(BaseModel):
    user_id: str
    reason: str = Field(..., min_length=6)

class UserIdPackageName(BaseModel):
    user_id: str
    package_name: str

class UserIdAmountMethod(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0)
    method: PaymentMethod

class UserIdTicketId(BaseModel):
    user_id: str
    ticket_id: str

class TcNameEmail(BaseModel):
    tc: str = Field(..., description="11 haneli T.C. kimlik no (sadece rakam)")
    name: str = Field(..., description="Kullanıcının adı ve soyadı")
    email: EmailStr = Field(..., description="Geçerli e-posta adresi")
    package: str = Field(..., description="Kullanıcının almak istediği paket adı")
    package_id: str = Field(..., description="Paketin benzersiz kimlik numarası")
    line_status: str = Field(..., description="Hattın durumu (ör. Aktif, Beklemede, Kapalı)")

    @field_validator("tc")
    @classmethod
    def validate_tc(cls, v: str) -> str:
        s = v.strip()
        if not re.fullmatch(r"\d{11}", s):
            raise ValueError("TC 11 haneli rakamlardan oluşmalıdır.")
        return s


class UserIdChallenge(BaseModel):
    tc: str
    challenge_response: str = Field(..., description="Kimlik doğrulama cevabı (örn. TC)")

class UserIdCampaignId(BaseModel):
    user_id: str
    campaign_id: str

class CreateTicket(BaseModel):
    user_id: str
    service_type: ServiceType
    description: str = Field(..., min_length=5, max_length=1000)


def get_package_information(user_id: str):
    return t.get_package_information(user_id=user_id)

def cancel_current_package(user_id: str):
    return t.cancel_current_package(user_id=user_id)

def get_bill_info(user_id: str, month:  str):
    return t.get_bill_info(user_id=user_id, month=month)

def get_user_info(user_id: str):
    return t.get_user_info(user_id=user_id)

def initiate_package_change(user_id: str, package_id: str):
    return t.initiate_package_change(user_id=user_id, package_id=package_id)

def get_available_packages(user_id: str):
    return t.get_available_packages(user_id=user_id)

def get_additional_packages(user_id: str):
    return t.get_additional_packages(user_id=user_id)

def submit_feedback(user_id: str, feedback_text: str, rating: Optional[int] = None):
    return t.submit_feedback(user_id=user_id, feedback_text=feedback_text, rating=rating)

def request_additional_package(user_id: str, package_type: str, package_name: str, quantity: int = 1):
    return t.request_additional_package(user_id=user_id, package_type=package_type, package_name=package_name, quantity=quantity)

def initiate_billing_dispute(user_id: str, reason: str):
    return t.initiate_billing_dispute(user_id=user_id, reason=reason)

def get_package_id_by_name(user_id: str, package_name: str):
    return t.get_package_id_by_name(user_id=user_id, package_name=package_name)

def get_line_status(user_id: str):
    return t.get_line_status(user_id=user_id)

def pay_bill(user_id: str, amount: float, method:str):
    return t.pay_bill(user_id=user_id, amount=amount, method=method)

def get_outstanding_balance(user_id: str):
    return t.get_outstanding_balance(user_id=user_id)

def cancel_support_ticket(user_id: str, ticket_id: str):
    return t.cancel_support_ticket(user_id=user_id, ticket_id=ticket_id)

def get_ticket_status(user_id: str, ticket_id: str):
    return t.get_ticket_status(user_id=user_id, ticket_id=ticket_id)

def create_support_ticket(user_id: str, service_type: str, description: str):
    return t.create_support_ticket(user_id=user_id, service_type=service_type, description=description)

def join_campaign(user_id: str, campaign_id: str):
    return t.join_campaign(user_id=user_id, campaign_id=campaign_id)

def get_campaigns(user_id:str):
    return t.get_campaigns(user_id=user_id)



#Araç kaydı: StructuredTool.from_function(...) ile fonksiyonları sarmalayıp lc_tools listesine koyma
tool_registry = [
    StructuredTool.from_function(
        name = "get_package_information",
        description = "Kullanıcının mevcut paket bilgisini verir.",
        func = get_package_information,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "cancel_current_package",
        description = "Mevcut paketi iptal eder.",
        func = cancel_current_package,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "get_bill_info",
        description = "Kullanıcının belirli aya ait fatura bilgisini alır.",
        func = get_bill_info,
        args_schema = UserIdMonth,
    ),
    StructuredTool.from_function(
        name = "get_user_info",
        description = "Kullanıcının adı, email adresi ve mevcut paketi gibi temel bilgileri verir.",
        func = get_user_info,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "initiate_package_change",
        description = "Kullanıcıyı yeni pakete geçirir. Paket değişikliği yapar.",
        func = initiate_package_change,
        args_schema = UserIdPackageId,
    ),
    StructuredTool.from_function(
        name = "get_available_packages",
        description = "Kullanıcının geçebileceği uygun yeni paketleri listeler.",
        func = get_available_packages,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "get_additional_packages",
        description = "Kullanıcının geçebileceği uygun ek paketleri listeler.",
        func = get_additional_packages,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "submit_feedback",
        description = "Kullanıcının sistemle veya paketlerle ilgili geri bildirimini kaydeder.",
        func = submit_feedback,
        args_schema = UserIdFeedback,
    ),
    StructuredTool.from_function(
        name = "request_additional_package",
        description = "Kullanıcının ek paket talebini başlatır.",
        func = request_additional_package,
        args_schema = UserIdExtraPackage,
    ),
    StructuredTool.from_function(
        name = "initiate_billing_dispute",
        description = "Belirtilen kullanıcının fatura itirazını kaydeder.",
        func = initiate_billing_dispute,
        args_schema = UserIdReason,
    ),
    StructuredTool.from_function(
        name = "get_package_id_by_name",
        description = "Kullanıcının erişebileceği paketler arasında ada göre paket ID'si döndürür.",
        func = get_package_id_by_name,
        args_schema = UserIdPackageName,
    ),
    StructuredTool.from_function(
        name = "get_line_status",
        description = "Kullanıcıya ait hattın durum bilgisini verir.",
        func = get_line_status,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "pay_bill",
        description = "Kullanıcının faturayı ödeme işlemini gerçekleştirir.",
        func = pay_bill,
        args_schema = UserIdAmountMethod,
    ),
    StructuredTool.from_function(
        name = "get_outstanding_balance",
        description = "Ödenmemiş fatura borcunun toplamını döndürür.",
        func = get_outstanding_balance,
        args_schema = UserId,
    ),
    StructuredTool.from_function(
        name = "cancel_support_ticket",
        description = "Belirtilen destek talebini iptal eder.",
        func = cancel_support_ticket,
        args_schema = UserIdTicketId,
    ),
    StructuredTool.from_function(
        name = "get_ticket_status",
        description = "Belirli bir destek talebinin güncel durumunu getirir.",
        func = get_ticket_status,
        args_schema = UserIdTicketId,
    ),
    StructuredTool.from_function(
        name = "create_support_ticket",
        description = "Yeni bir teknik destek talebi oluşturur.",
        func = create_support_ticket,
        args_schema = CreateTicket
    ),
    StructuredTool.from_function(
        name = "join_campaign",
        description = "Kullanıcıyı belirtilen kampanyaya katar.",
        func = join_campaign,
        args_schema = UserIdCampaignId,
    ),
    StructuredTool.from_function(
        name = "get_campaigns",
        description = "Kullanıcının katılabileceği güncel kampanyaları getirir.",
        func = get_campaigns,
        args_schema = UserId,
    )
]

#  dict olarak da erişim gerekirse:
# tool_registry = {tool.name: tool for tool in lc_tools}
