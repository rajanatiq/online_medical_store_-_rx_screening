"""
models.py
=========
SQLAlchemy ORM models for: Online Medical Store & Rx Screening
Generated exactly as per OnlineMedicalStore SQL Server schema.

NOTE:
- Yeh file tumhare existing `database.py` se `Base` import karti hai.
  Agar tumhara database.py mein `Base = declarative_base()` already defined hai,
  to neeche wali import line waisi hi rehne do.
- Sab table/column names EXACT SQL schema jaise hi rakhe gaye hain
  (lowercase, jaise wo SQL script mein the) — kahin bhi auto Python-style
  renaming nahi ki gayi, taake FK mapping mismatch na ho.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Numeric,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# =====================================================================
# USER  (login identity for Customer / Store / SuperAdmin)
# =====================================================================
class User(Base):
    __tablename__ = "user"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(150), nullable=False, unique=True)
    password = Column(String(250), nullable=False)
    Role = Column(String(50), nullable=False)  # 'Customer' | 'Store' | 'SuperAdmin'

    # relationships
    customer = relationship("Customer", back_populates="user", uselist=False)
    medicalstore = relationship("MedicalStore", back_populates="user", uselist=False)
    store_ratings = relationship("StoreRating", back_populates="user")


# =====================================================================
# CUSTOMER
# =====================================================================
class Customer(Base):
    __tablename__ = "customer"

    c_id = Column(Integer, ForeignKey("user.Id"), primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    password = Column(String(250), nullable=False)
    contact = Column(String(20))
    dob = Column(Date)

    # relationships
    user = relationship("User", back_populates="customer")
    profiles = relationship("Profile", back_populates="customer")
    prescriptions = relationship("Prescription", back_populates="customer")
    orders = relationship("Order", back_populates="customer")


# =====================================================================
# PROFILES  (self / family member health profiles)
# =====================================================================
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cus_id = Column(Integer, ForeignKey("customer.c_id"), nullable=False)
    Fullname = Column(String(150), nullable=False)
    relation = Column(String(50), nullable=False)  # 'Self','Spouse','Child','Parent',...
    gender = Column(String(20))
    contact = Column(String(20))
    age = Column(Integer)
    default_lat = Column(Float)
    default_long = Column(Float)
    Addres = Column(String(250))
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    customer = relationship("Customer", back_populates="profiles")
    prescriptions = relationship("Prescription", back_populates="profile")
    phr_entries = relationship("PHR", back_populates="profile")
    orders = relationship("Order", back_populates="profile")


# =====================================================================
# MEDICALSTORE  (pharmacy branch)
# =====================================================================
class MedicalStore(Base):
    __tablename__ = "medicalstore"

    store_id = Column(Integer, ForeignKey("user.Id"), primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    chain_name = Column(String(150), nullable=True)   # e.g. 'Shaheen Chemist', 'D-Watson' — NULL = independent
    location = Column(String(250))
    images = Column(String(250), nullable=True)
    password = Column(String(250), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

    # relationships
    user = relationship("User", back_populates="medicalstore")
    medicines = relationship("Medicine", back_populates="medicalstore")
    orders = relationship("Order", back_populates="medicalstore")
    store_ratings = relationship("StoreRating", back_populates="medicalstore")


# =====================================================================
# MEDICINE  (per-store catalog)
# =====================================================================
class Medicine(Base):
    __tablename__ = "medicine"

    med_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("medicalstore.store_id"), nullable=False)
    name = Column(String(150), nullable=False)
    base_name = Column(String(150), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    pills_per_pack = Column(Integer)
    category = Column(String(100))
    strength = Column(String(50))

    # relationships
    medicalstore = relationship("MedicalStore", back_populates="medicines")
    batches = relationship("MedicineBatch", back_populates="medicine")
    order_items = relationship("OrderItem", back_populates="medicine")


# =====================================================================
# MEDICINE_BATCHES  (stock / expiry tracking)
# =====================================================================
class MedicineBatch(Base):
    __tablename__ = "medicine_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    med_id = Column(Integer, ForeignKey("medicine.med_id"), nullable=False)
    batch_number = Column(String(100), nullable=False)
    total_pills = Column(Integer, nullable=False)
    remaining_pills = Column(Integer, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    purchase_price_per_pack = Column(Numeric(10, 2))

    # relationships
    medicine = relationship("Medicine", back_populates="batches")


# =====================================================================
# PRESCRIPTIONS  (uploaded Rx image per order context)
# =====================================================================
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cust_id = Column(Integer, ForeignKey("customer.c_id"), nullable=False)
    profileid = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    location = Column(String(250))
    rx_image = Column(String(250), nullable=False)

    # relationships
    customer = relationship("Customer", back_populates="prescriptions")
    profile = relationship("Profile", back_populates="prescriptions")
    prescription_medicines = relationship(
        "PrescriptionMedicine", back_populates="prescription"
    )


# =====================================================================
# PRESCRIPTION_MEDICINE  (doctor's Rx lines, dosage split by time)
# =====================================================================
class PrescriptionMedicine(Base):
    __tablename__ = "prescription_medicine"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prescription_id = Column(
        Integer, ForeignKey("prescriptions.id"), nullable=False
    )
    medicine_name = Column(String(150), nullable=False)
    potency = Column(String(50))
    days = Column(Integer, nullable=False)
    total_quantity = Column(Integer, nullable=False)
    morning_pills = Column(Integer, default=0)
    evening_pills = Column(Integer, default=0)
    night_pills = Column(Integer, default=0)

    # relationships
    prescription = relationship(
        "Prescription", back_populates="prescription_medicines"
    )


# =====================================================================
# PHR  (Personal Health Record — disease / current meds)
# =====================================================================
class PHR(Base):
    __tablename__ = "phr"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    entry_name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)  # 'PastDisease' | 'AlreadyTakingMedicine'

    # relationships
    profile = relationship("Profile", back_populates="phr_entries")


# =====================================================================
# CONTRAINDICATION  (drug safety rules engine)
# =====================================================================
class Contraindication(Base):
    __tablename__ = "contraindication"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    base_name = Column(String(150), nullable=False)
    disease = Column(String(150), nullable=True)
    with_base = Column(String(150), nullable=True)
    severity = Column(String(20), nullable=False)  # 'High' | 'Moderate'
    message = Column(String(250), nullable=False)


# =====================================================================
# MEDLIST  (master reference list of known medicines)
# =====================================================================
class MedList(Base):
    __tablename__ = "medlist"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    medicne_name = Column(String(250), nullable=False)  # NOTE: spelling matches SQL script exactly
    base_name = Column(String(250), nullable=False)
    potency = Column(String(250))
    category = Column(String(250))


# =====================================================================
# ORDERS  (one order per pickup transaction)
# =====================================================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cust_id = Column(Integer, ForeignKey("customer.c_id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("medicalstore.store_id"), nullable=False)
    status = Column(String(30), nullable=False, default="Pending")
    # 'Pending' | 'Prescription Verified' | 'Ready for Pickup' | 'Completed' | 'Rejected'
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    order_date = Column(DateTime, nullable=False, server_default=func.now())

    # relationships
    customer = relationship("Customer", back_populates="orders")
    profile = relationship("Profile", back_populates="orders")
    medicalstore = relationship("MedicalStore", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


# =====================================================================
# ORDER_ITEMS  (medicines within an order)
# =====================================================================
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    med_id = Column(Integer, ForeignKey("medicine.med_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    # relationships
    order = relationship("Order", back_populates="order_items")
    medicine = relationship("Medicine", back_populates="order_items")


# =====================================================================
# STORE_RATING  (customer feedback after pickup)
# =====================================================================
class StoreRating(Base):
    __tablename__ = "Store_Rating"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("medicalstore.store_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.Id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    review = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # relationships
    medicalstore = relationship("MedicalStore", back_populates="store_ratings")
    user = relationship("User", back_populates="store_ratings")