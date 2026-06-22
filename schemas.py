"""
schemas.py
==========
Pydantic schemas for: Online Medical Store & Rx Screening
Yeh file `models.py` ke 14 SQLAlchemy models ke hisab se bani hai.

Pattern follow kiya gaya hai (har table ke liye):
    - XBase    -> common fields (create + update dono mein use honge)
    - XCreate  -> jo client POST request mein bhejega (ID/timestamps exclude)
    - XOut     -> jo API response mein wapis jayega (ID + DB-generated fields included)

FIXES in this version:
    - OrderItemCreate: order_id hata diya (controller set karta hai internally)
    - MedicalStoreBase: chain_name add kiya (pharmacy chain grouping)
    - PrescriptionBase: status add kiya (Pending/Approved/Rejected)
    - OrderCreate/Out: prescription_id add kiya (optional Rx link)
    - CustomerRegister: naya unified schema (User + Customer ek call mein)
    - NearbyStoresRequest/StoreWithDistanceOut: nearest branch API ke liye
    - PrescriptionStatusUpdate: staff ke liye approve/reject schema
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# =====================================================================
# USER
# =====================================================================
class UserBase(BaseModel):
    email: EmailStr
    Role: str  # 'Customer' | 'Store' | 'SuperAdmin'


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    Id: int

    class Config:
        from_attributes = True  # Pydantic v1 mein: orm_mode = True


# =====================================================================
# CUSTOMER REGISTRATION  (Unified — User + Customer ek hi API call mein)
# =====================================================================
class CustomerRegister(BaseModel):
    """
    Mobile app registration ke liye: ek POST /register call karo.
    Backend internally pehle User banata hai, phir Customer record link karta hai.
    """
    name: str
    email: EmailStr
    password: str
    contact: Optional[str] = None
    dob: Optional[date] = None


class CustomerRegisterOut(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    message: str = "Registration successful"

    class Config:
        from_attributes = True


# =====================================================================
# CUSTOMER
# =====================================================================
class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    contact: Optional[str] = None
    dob: Optional[date] = None


class CustomerCreate(CustomerBase):
    c_id: int   # user.Id se match karna hai (agar manually create kar rahe ho)
    password: str


class CustomerOut(CustomerBase):
    c_id: int

    class Config:
        from_attributes = True


# =====================================================================
# PROFILES
# =====================================================================
class ProfileBase(BaseModel):
    Fullname: str
    relation: str   # 'Self','Spouse','Child','Parent',...
    gender: Optional[str] = None
    contact: Optional[str] = None
    age: Optional[int] = None
    default_lat: Optional[float] = None
    default_long: Optional[float] = None
    Addres: Optional[str] = None
    is_active: bool = True


class ProfileCreate(ProfileBase):
    cus_id: int


class ProfileOut(ProfileBase):
    id: int
    cus_id: int

    class Config:
        from_attributes = True


# =====================================================================
# MEDICALSTORE
# =====================================================================
class MedicalStoreBase(BaseModel):
    name: str
    email: EmailStr
    chain_name: Optional[str] = None   # 'Shaheen Chemist', 'D-Watson', etc. — NULL = independent
    location: Optional[str] = None
    images: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MedicalStoreCreate(MedicalStoreBase):
    store_id: int   # user.Id se match karna hai
    password: str


class MedicalStoreOut(MedicalStoreBase):
    store_id: int

    class Config:
        from_attributes = True


class StoreWithDistanceOut(MedicalStoreOut):
    """Nearby stores endpoint ke liye — distance_km bhi include hota hai."""
    distance_km: float


# =====================================================================
# MEDICINE
# =====================================================================
class MedicineBase(BaseModel):
    name: str
    base_name: str
    price: Decimal
    pills_per_pack: Optional[int] = None
    category: Optional[str] = None
    strength: Optional[str] = None


class MedicineCreate(MedicineBase):
    store_id: int


class MedicineOut(MedicineBase):
    med_id: int
    store_id: int

    class Config:
        from_attributes = True


# =====================================================================
# MEDICINE_BATCHES
# =====================================================================
class MedicineBatchBase(BaseModel):
    batch_number: str
    total_pills: int
    remaining_pills: int
    expiry_date: datetime
    purchase_price_per_pack: Optional[Decimal] = None


class MedicineBatchCreate(MedicineBatchBase):
    med_id: int


class MedicineBatchOut(MedicineBatchBase):
    id: int
    med_id: int

    class Config:
        from_attributes = True


# =====================================================================
# PRESCRIPTIONS
# =====================================================================
class PrescriptionBase(BaseModel):
    location: Optional[str] = None
    rx_image: str
    status: str = "Pending"  # 'Pending' | 'Approved' | 'Rejected'


class PrescriptionCreate(PrescriptionBase):
    cust_id: int
    profileid: int


class PrescriptionOut(PrescriptionBase):
    id: int
    cust_id: int
    profileid: int

    class Config:
        from_attributes = True


class PrescriptionStatusUpdate(BaseModel):
    """Staff ke liye: prescription approve ya reject karo."""
    status: str  # 'Approved' | 'Rejected'


# =====================================================================
# PRESCRIPTION_MEDICINE
# =====================================================================
class PrescriptionMedicineBase(BaseModel):
    medicine_name: str
    potency: Optional[str] = None
    days: int
    total_quantity: int
    morning_pills: int = 0
    evening_pills: int = 0
    night_pills: int = 0


class PrescriptionMedicineCreate(PrescriptionMedicineBase):
    prescription_id: int


class PrescriptionMedicineOut(PrescriptionMedicineBase):
    id: int
    prescription_id: int

    class Config:
        from_attributes = True


# =====================================================================
# PHR
# =====================================================================
class PHRBase(BaseModel):
    entry_name: str
    category: str   # 'PastDisease' | 'AlreadyTakingMedicine'


class PHRCreate(PHRBase):
    profile_id: int


class PHROut(PHRBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True


# =====================================================================
# CONTRAINDICATION
# =====================================================================
class ContraindicationBase(BaseModel):
    base_name: str
    disease: Optional[str] = None
    with_base: Optional[str] = None
    severity: str   # 'High' | 'Moderate'
    message: str


class ContraindicationCreate(ContraindicationBase):
    pass


class ContraindicationOut(ContraindicationBase):
    id: int

    class Config:
        from_attributes = True


# =====================================================================
# MEDLIST
# =====================================================================
class MedListBase(BaseModel):
    medicne_name: str   # NOTE: spelling matches models.py / SQL script exactly
    base_name: str
    potency: Optional[str] = None
    category: Optional[str] = None


class MedListCreate(MedListBase):
    pass


class MedListOut(MedListBase):
    id: int

    class Config:
        from_attributes = True


# =====================================================================
# ORDERS
# =====================================================================
class OrderBase(BaseModel):
    status: str = "Pending"
    # 'Pending' | 'Prescription Verified' | 'Ready for Pickup' | 'Completed' | 'Rejected'
    total_amount: Decimal = Decimal("0")


class OrderCreate(OrderBase):
    cust_id: int
    profile_id: int
    store_id: int
    prescription_id: Optional[int] = None   # optional — sirf tab jab Rx required ho


class OrderOut(OrderBase):
    id: int
    cust_id: int
    profile_id: int
    store_id: int
    prescription_id: Optional[int] = None
    order_date: datetime

    class Config:
        from_attributes = True


# Order with its line items nested (useful for "view order details" endpoint)
class OrderWithItemsOut(OrderOut):
    order_items: List["OrderItemOut"] = []

    class Config:
        from_attributes = True


# =====================================================================
# ORDER_ITEMS
# =====================================================================
class OrderItemBase(BaseModel):
    quantity: int
    unit_price: Decimal


class OrderItemCreate(OrderItemBase):
    """
    FIX: order_id yahan nahi hota — order create hone ke baad controller
    internally set karta hai. Client sirf med_id + quantity + unit_price bhejta hai.
    """
    med_id: int


class OrderItemOut(OrderItemBase):
    id: int
    order_id: int
    med_id: int

    class Config:
        from_attributes = True


# Resolve forward reference used in OrderWithItemsOut
OrderWithItemsOut.model_rebuild()


# =====================================================================
# STORE_RATING
# =====================================================================
class StoreRatingBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)   # 1 to 5
    review: Optional[str] = None


class StoreRatingCreate(StoreRatingBase):
    store_id: int
    user_id: int


class StoreRatingOut(StoreRatingBase):
    id: int
    store_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# NEARBY STORES REQUEST
# =====================================================================
class NearbyStoresRequest(BaseModel):
    """
    Customer ke lat/long se nearest branches dhundne ke liye.
    radius_km default: 10 km
    """
    lat: float
    long: float
    radius_km: float = 10.0
    chain_name: Optional[str] = None   # optional: sirf ek chain ki branches