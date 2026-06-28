

import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
import schemas


# =====================================================================
# 1. AUTH HELPERS
# =====================================================================
SECRET_KEY = "CHANGE_THIS_SECRET_KEY"  # production mein .env se load karo
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 din

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, email: str, password: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Wrong Email or Password")

    # Password verify karo:
    # - Production mein bcrypt hash hota hai → verify_password() use hoti hai
    # - Seed data mein plain text '1234' store hai → direct compare fallback
    password_ok = False
    try:
        password_ok = verify_password(password, user.password)
    except Exception:
        # bcrypt fail kare (e.g. plain-text hash nahi) → direct compare karo
        password_ok = (password == user.password)

    if not password_ok:
        raise HTTPException(status_code=401, detail="Wrong Email or password")

    return user


# =====================================================================
# 2. USER
# =====================================================================
def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    # check karo email pehle se registered toh nahi
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="This Email is already Registered")

    new_user = models.User(
        email=user.email,
        password=get_password_hash(user.password),
        Role=user.Role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_user(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.Id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    return user


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    db.delete(user)
    db.commit()


# =====================================================================
# 2b. UNIFIED CUSTOMER REGISTRATION  (User + Customer ek call mein)
# =====================================================================
def register_customer(db: Session, data: schemas.CustomerRegister) -> dict:
    """
    Mobile app registration flow:
    1. Email duplicate check
    2. User record banao (Role = 'Customer')
    3. Customer record banao (same ID link)
    4. Sab kuch ek transaction mein — agar kuch fail ho to rollback
    """
    # Step 1: duplicate email check
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="This Email is already registered")

    try:
        # Step 2: User banao
        new_user = models.User(
            email=data.email,
            password=get_password_hash(data.password),
            Role="Customer",
        )
        db.add(new_user)
        db.flush()  # ID generate karo bina commit ke

        # Step 3: Customer banao (same ID)
        new_customer = models.Customer(
            c_id=new_user.Id,
            name=data.name,
            email=data.email,
            password=get_password_hash(data.password),
            contact=data.contact,
            dob=data.dob,
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_user)

        return {
            "user_id": new_user.Id,
            "name": data.name,
            "email": data.email,
            "message": "Registration successful",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration Failed: {str(e)}")


# =====================================================================
# 3. CUSTOMER
# =====================================================================
def create_customer(db: Session, customer: schemas.CustomerCreate) -> models.Customer:
    # linked user exist karta hai aur role Customer hai
    user = get_user(db, customer.c_id)
    if user.Role != "Customer":
        raise HTTPException(status_code=400, detail="Linked User Role is not a Customer")

    new_customer = models.Customer(
        c_id=customer.c_id,
        name=customer.name,
        email=customer.email,
        password=get_password_hash(customer.password),
        contact=customer.contact,
        dob=customer.dob,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


def get_customer(db: Session, c_id: int) -> models.Customer:
    customer = db.query(models.Customer).filter(models.Customer.c_id == c_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer Not Found")
    return customer


def get_all_customers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Customer]:
    return db.query(models.Customer).offset(skip).limit(limit).all()


def update_customer(db: Session, c_id: int, customer: schemas.CustomerBase) -> models.Customer:
    db_customer = get_customer(db, c_id)
    db_customer.name = customer.name
    db_customer.email = customer.email
    db_customer.contact = customer.contact
    db_customer.dob = customer.dob
    db.commit()
    db.refresh(db_customer)
    return db_customer


def delete_customer(db: Session, c_id: int) -> None:
    db_customer = get_customer(db, c_id)
    db.delete(db_customer)
    db.commit()


# =====================================================================
# 4. PROFILE
# =====================================================================
def create_profile(db: Session, profile: schemas.ProfileCreate) -> models.Profile:
    get_customer(db, profile.cus_id)  # customer exist karta hai check

    new_profile = models.Profile(**profile.model_dump())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


def get_profile(db: Session, profile_id: int) -> models.Profile:
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not Found")
    return profile


def get_profiles_by_customer(db: Session, cus_id: int) -> List[models.Profile]:
    # sirf active profiles return karo
    return db.query(models.Profile).filter(
        models.Profile.cus_id == cus_id,
        models.Profile.is_active == True
    ).all()


def update_profile(db: Session, profile_id: int, profile: schemas.ProfileBase) -> models.Profile:
    db_profile = get_profile(db, profile_id)
    for field, value in profile.model_dump().items():
        setattr(db_profile, field, value)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def delete_profile(db: Session, profile_id: int) -> None:
    # soft delete — record rakhte hain, sirf inactive karte hain
    db_profile = get_profile(db, profile_id)
    db_profile.is_active = False
    db.commit()


# =====================================================================
# 5. MEDICAL STORE
# =====================================================================
def create_medicalstore(db: Session, store: schemas.MedicalStoreCreate) -> models.MedicalStore:
    user = get_user(db, store.store_id)
    if user.Role != "Store":
        raise HTTPException(status_code=400, detail="Linked user role is not a Store")

    new_store = models.MedicalStore(
        store_id=store.store_id,
        name=store.name,
        email=store.email,
        chain_name=store.chain_name,
        location=store.location,
        images=store.images,
        password=get_password_hash(store.password),
        latitude=store.latitude,
        longitude=store.longitude,
    )
    db.add(new_store)
    db.commit()
    db.refresh(new_store)
    return new_store


def get_medicalstore(db: Session, store_id: int) -> models.MedicalStore:
    store = db.query(models.MedicalStore).filter(models.MedicalStore.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Medical Store not found")
    return store


def get_all_medicalstores(db: Session, skip: int = 0, limit: int = 100) -> List[models.MedicalStore]:
    return db.query(models.MedicalStore).offset(skip).limit(limit).all()


def update_medicalstore(db: Session, store_id: int, store: schemas.MedicalStoreBase) -> models.MedicalStore:
    db_store = get_medicalstore(db, store_id)
    for field, value in store.model_dump().items():
        setattr(db_store, field, value)
    db.commit()
    db.refresh(db_store)
    return db_store


def delete_medicalstore(db: Session, store_id: int) -> None:
    db_store = get_medicalstore(db, store_id)
    db.delete(db_store)
    db.commit()


# ─── 5b. STORE FILTERS ────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula: do GPS coordinates ke beech ki distance km mein.
    """
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_nearby_stores(
    db: Session,
    lat: float,
    long: float,
    radius_km: float = 10.0,
    chain_name: Optional[str] = None,
) -> List[dict]:
    """
    Customer ke lat/long se sab stores ki distance calculate karo.
    Jo radius_km ke andar hain unhe sorted (nearest first) return karo.
    Optional: sirf ek chain ke branches filter karo.
    """
    query = db.query(models.MedicalStore).filter(
        models.MedicalStore.latitude.isnot(None),
        models.MedicalStore.longitude.isnot(None),
    )

    if chain_name:
        query = query.filter(models.MedicalStore.chain_name == chain_name)

    all_stores = query.all()
    results = []

    for store in all_stores:
        dist = _haversine_km(lat, long, store.latitude, store.longitude)
        if dist <= radius_km:
            results.append({
                "store_id": store.store_id,
                "name": store.name,
                "email": store.email,
                "chain_name": store.chain_name,
                "location": store.location,
                "images": store.images,
                "latitude": store.latitude,
                "longitude": store.longitude,
                "distance_km": round(dist, 2),
            })

    # nearest pehle
    results.sort(key=lambda x: x["distance_km"])
    return results


def get_stores_by_chain(db: Session, chain_name: str) -> List[models.MedicalStore]:
    """Ek pharmacy chain ki sab branches lo."""
    return db.query(models.MedicalStore).filter(
        models.MedicalStore.chain_name == chain_name
    ).all()


def get_all_chain_names(db: Session) -> dict:
    """
    Database mein jo bhi unique chain names hain (NULL exclude) wo return karo.
    Frontend dropdown populate karne ke liye use hoga.
    """
    rows = (
        db.query(models.MedicalStore.chain_name)
        .filter(models.MedicalStore.chain_name.isnot(None))
        .distinct()
        .all()
    )
    chains = sorted([r[0] for r in rows if r[0]])
    return {"chains": chains}


# =====================================================================
# 6. MEDICINE
# =====================================================================
def create_medicine(db: Session, medicine: schemas.MedicineCreate) -> models.Medicine:
    get_medicalstore(db, medicine.store_id)  # store exist karta hai check

    new_medicine = models.Medicine(**medicine.model_dump())
    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)
    return new_medicine


def get_medicine(db: Session, med_id: int) -> models.Medicine:
    medicine = db.query(models.Medicine).filter(models.Medicine.med_id == med_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine nahi mili")
    return medicine


def get_medicines_by_store(db: Session, store_id: int) -> List[models.Medicine]:
    return db.query(models.Medicine).filter(models.Medicine.store_id == store_id).all()


def search_medicines(db: Session, query: str) -> List[models.Medicine]:
    pattern = f"%{query}%"
    return db.query(models.Medicine).filter(
        (models.Medicine.name.ilike(pattern)) |
        (models.Medicine.base_name.ilike(pattern))
    ).all()


def update_medicine(db: Session, med_id: int, medicine: schemas.MedicineBase) -> models.Medicine:
    db_medicine = get_medicine(db, med_id)
    for field, value in medicine.model_dump().items():
        setattr(db_medicine, field, value)
    db.commit()
    db.refresh(db_medicine)
    return db_medicine


def delete_medicine(db: Session, med_id: int) -> None:
    db_medicine = get_medicine(db, med_id)
    db.delete(db_medicine)
    db.commit()


# =====================================================================
# 7. MEDICINE BATCH
# =====================================================================
def create_medicine_batch(db: Session, batch: schemas.MedicineBatchCreate) -> models.MedicineBatch:
    get_medicine(db, batch.med_id)  # medicine exist karta hai check

    new_batch = models.MedicineBatch(**batch.model_dump())
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    return new_batch


def get_medicine_batch(db: Session, batch_id: int) -> models.MedicineBatch:
    batch = db.query(models.MedicineBatch).filter(models.MedicineBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Medicine Batchnot found")
    return batch


def get_batches_by_medicine(db: Session, med_id: int) -> List[models.MedicineBatch]:
    # pehle expire hone wali batch pehle aaye (FEFO order)
    return db.query(models.MedicineBatch).filter(
        models.MedicineBatch.med_id == med_id
    ).order_by(models.MedicineBatch.expiry_date.asc()).all()


def get_total_stock(db: Session, med_id: int) -> int:
    batches = get_batches_by_medicine(db, med_id)
    return sum(b.remaining_pills for b in batches)


def reduce_batch_stock(db: Session, med_id: int, quantity: int) -> None:
    """
    FEFO (First-Expiry-First-Out) — pehle expire hone wali batch se
    pehle stock khatam karo.
    """
    batches = get_batches_by_medicine(db, med_id)
    remaining = quantity

    for batch in batches:
        if remaining <= 0:
            break
        deduct = min(batch.remaining_pills, remaining)
        batch.remaining_pills -= deduct
        remaining -= deduct

    if remaining > 0:
        raise HTTPException(status_code=400, detail="Stock not Available")

    db.commit()


def delete_medicine_batch(db: Session, batch_id: int) -> None:
    db_batch = get_medicine_batch(db, batch_id)
    db.delete(db_batch)
    db.commit()


# =====================================================================
# 8. PRESCRIPTION
# =====================================================================
def create_prescription(db: Session, prescription: schemas.PrescriptionCreate) -> models.Prescription:
    get_customer(db, prescription.cust_id)
    get_profile(db, prescription.profileid)

    new_prescription = models.Prescription(**prescription.model_dump())
    db.add(new_prescription)
    db.commit()
    db.refresh(new_prescription)
    return new_prescription


def get_prescription(db: Session, prescription_id: int) -> models.Prescription:
    prescription = db.query(models.Prescription).filter(
        models.Prescription.id == prescription_id
    ).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


def get_prescriptions_by_customer(db: Session, cust_id: int) -> List[models.Prescription]:
    return db.query(models.Prescription).filter(
        models.Prescription.cust_id == cust_id
    ).all()


VALID_PRESCRIPTION_STATUSES = ["Pending", "Approved", "Rejected"]


def update_prescription_status(db: Session, prescription_id: int, status: str) -> models.Prescription:
    """
    Pharmacy staff ke liye: prescription approve ya reject karo.
    Sirf valid status values accept karta hai.
    """
    if status not in VALID_PRESCRIPTION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid options: {VALID_PRESCRIPTION_STATUSES}"
        )
    prescription = get_prescription(db, prescription_id)
    prescription.status = status
    db.commit()
    db.refresh(prescription)
    return prescription


def delete_prescription(db: Session, prescription_id: int) -> None:
    db_prescription = get_prescription(db, prescription_id)
    db.delete(db_prescription)
    db.commit()


# =====================================================================
# 9. PRESCRIPTION MEDICINE
# =====================================================================
def create_prescription_medicine(db: Session, pm: schemas.PrescriptionMedicineCreate) -> models.PrescriptionMedicine:
    get_prescription(db, pm.prescription_id)

    new_pm = models.PrescriptionMedicine(**pm.model_dump())
    db.add(new_pm)
    db.commit()
    db.refresh(new_pm)
    return new_pm


def get_prescription_medicines(db: Session, prescription_id: int) -> List[models.PrescriptionMedicine]:
    return db.query(models.PrescriptionMedicine).filter(
        models.PrescriptionMedicine.prescription_id == prescription_id
    ).all()


def delete_prescription_medicine(db: Session, pm_id: int) -> None:
    pm = db.query(models.PrescriptionMedicine).filter(
        models.PrescriptionMedicine.id == pm_id
    ).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Prescription medicine entry not Found")
    db.delete(pm)
    db.commit()


# =====================================================================
# 10. PHR (Personal Health Record)
# =====================================================================
def create_phr_entry(db: Session, phr: schemas.PHRCreate) -> models.PHR:
    get_profile(db, phr.profile_id)

    new_phr = models.PHR(**phr.model_dump())
    db.add(new_phr)
    db.commit()
    db.refresh(new_phr)
    return new_phr


def get_phr_by_profile(db: Session, profile_id: int) -> List[models.PHR]:
    return db.query(models.PHR).filter(models.PHR.profile_id == profile_id).all()


def delete_phr_entry(db: Session, phr_id: int) -> None:
    phr = db.query(models.PHR).filter(models.PHR.id == phr_id).first()
    if not phr:
        raise HTTPException(status_code=404, detail="PHR entry not Found")
    db.delete(phr)
    db.commit()


# =====================================================================
# 11. CONTRAINDICATION + DRUG SAFETY CHECK
# =====================================================================
def create_contraindication(db: Session, rule: schemas.ContraindicationCreate) -> models.Contraindication:
    new_rule = models.Contraindication(**rule.model_dump())
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


def get_all_contraindications(db: Session, skip: int = 0, limit: int = 100) -> List[models.Contraindication]:
    return db.query(models.Contraindication).offset(skip).limit(limit).all()


def delete_contraindication(db: Session, rule_id: int) -> None:
    rule = db.query(models.Contraindication).filter(
        models.Contraindication.id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Contraindication rule not Found")
    db.delete(rule)
    db.commit()


def check_medicine_safety(db: Session, profile_id: int, med_ids: List[int]) -> List[dict]:
    """
    Order confirm karne se pehle drug safety check karta hai.

    Steps:
    1. Profile ki PHR se bimariyan aur current medicines nikalo
    2. Cart ki medicines ka base_name nikalo
    3. Contraindication table se 3 cheezein check karo:
       - Cart medicine vs Patient ki bimari
       - Cart medicine vs Patient ki current medicines
       - Cart medicine vs Cart ki doosri medicines (ek saath lene se nuksaan)
    4. Warnings return karo — customer decide kare proceed kare ya nahi
    """
    # Step 1: PHR se info nikalo
    phr_entries = get_phr_by_profile(db, profile_id)
    diseases = {e.entry_name for e in phr_entries if e.category == "PastDisease"}
    current_meds = {e.entry_name for e in phr_entries if e.category == "AlreadyTakingMedicine"}

    # Step 2: Cart ki medicines
    cart_medicines = [get_medicine(db, mid) for mid in med_ids]
    cart_base_names = {m.base_name for m in cart_medicines}

    # Step 3: Sab rules nikalo aur match karo
    all_rules = db.query(models.Contraindication).all()
    warnings = []

    for medicine in cart_medicines:
        for rule in all_rules:
            if rule.base_name != medicine.base_name:
                continue

            # Check 1: Medicine vs Patient ki bimari
            if rule.disease and rule.disease in diseases:
                warnings.append({
                    "medicine": medicine.name,
                    "type": "Medicine vs Disease",
                    "conflict_with": rule.disease,
                    "severity": rule.severity,
                    "message": rule.message,
                })

            # Check 2: Medicine vs Patient ki current medicines
            if rule.with_base and rule.with_base in current_meds:
                warnings.append({
                    "medicine": medicine.name,
                    "type": "Medicine vs Medicine (current medication)",
                    "conflict_with": rule.with_base,
                    "severity": rule.severity,
                    "message": rule.message,
                })

            # Check 3: Medicine vs Cart ki doosri medicine
            if rule.with_base and rule.with_base in cart_base_names and rule.with_base != medicine.base_name:
                warnings.append({
                    "medicine": medicine.name,
                    "type": "Medicine vs Medicine (in cart)",
                    "conflict_with": rule.with_base,
                    "severity": rule.severity,
                    "message": rule.message,
                })

    return warnings


# =====================================================================
# 12. MEDLIST
# =====================================================================
def create_medlist_entry(db: Session, entry: schemas.MedListCreate) -> models.MedList:
    new_entry = models.MedList(**entry.model_dump())
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


def get_all_medlist(db: Session, skip: int = 0, limit: int = 100) -> List[models.MedList]:
    return db.query(models.MedList).offset(skip).limit(limit).all()


def search_medlist(db: Session, query: str) -> List[models.MedList]:
    pattern = f"%{query}%"
    return db.query(models.MedList).filter(
        (models.MedList.medicne_name.ilike(pattern)) |
        (models.MedList.base_name.ilike(pattern))
    ).all()


def delete_medlist_entry(db: Session, entry_id: int) -> None:
    entry = db.query(models.MedList).filter(models.MedList.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Medlist entry not Found")
    db.delete(entry)
    db.commit()


# =====================================================================
# 13. ORDER
# =====================================================================
def create_order(
    db: Session,
    order: schemas.OrderCreate,
    items: List[schemas.OrderItemCreate]
) -> models.Order:
    """
    Order aur uske sab items ek saath banata hai.
    Har item ka stock bhi FEFO se deduct karta hai.
    prescription_id optional hai — agar order mein Rx required ho toh link karo.
    """
    get_customer(db, order.cust_id)
    get_profile(db, order.profile_id)
    get_medicalstore(db, order.store_id)

    # prescription exist karta hai? (agar diya gaya ho)
    if order.prescription_id is not None:
        get_prescription(db, order.prescription_id)

    if not items:
        raise HTTPException(status_code=400, detail="There should be atleast on item in Order")

    # Order banao
    new_order = models.Order(
        cust_id=order.cust_id,
        profile_id=order.profile_id,
        store_id=order.store_id,
        prescription_id=order.prescription_id,
        status=order.status,
        total_amount=order.total_amount,
    )
    db.add(new_order)
    db.flush()  # order.id generate karne ke liye (commit se pehle)

    # Har item ke liye stock deduct karo aur record banao
    for item in items:
        get_medicine(db, item.med_id)
        reduce_batch_stock(db, item.med_id, item.quantity)

        new_item = models.OrderItem(
            order_id=new_order.id,   # controller internally set karta hai
            med_id=item.med_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        db.add(new_item)

    db.commit()
    db.refresh(new_order)
    return new_order


def get_order(db: Session, order_id: int) -> models.Order:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not Found")
    return order


def get_orders_by_customer(db: Session, cust_id: int) -> List[models.Order]:
    return db.query(models.Order).filter(models.Order.cust_id == cust_id).all()


def get_orders_by_store(db: Session, store_id: int) -> List[models.Order]:
    return db.query(models.Order).filter(models.Order.store_id == store_id).all()


VALID_ORDER_STATUSES = [
    "Pending",
    "Prescription Verified",
    "Ready for Pickup",
    "Completed",
    "Rejected",
]


def update_order_status(db: Session, order_id: int, status_value: str) -> models.Order:
    if status_value not in VALID_ORDER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid options: {VALID_ORDER_STATUSES}"
        )
    order = get_order(db, order_id)
    order.status = status_value
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int) -> None:
    order = get_order(db, order_id)
    db.delete(order)
    db.commit()


# =====================================================================
# 14. ORDER ITEMS
# =====================================================================
def get_order_items(db: Session, order_id: int) -> List[models.OrderItem]:
    return db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()


def delete_order_item(db: Session, item_id: int) -> None:
    item = db.query(models.OrderItem).filter(models.OrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not Found")
    db.delete(item)
    db.commit()


# =====================================================================
# 15. STORE RATING
# =====================================================================
def create_store_rating(db: Session, rating: schemas.StoreRatingCreate) -> models.StoreRating:
    get_medicalstore(db, rating.store_id)
    get_user(db, rating.user_id)

    new_rating = models.StoreRating(**rating.model_dump())
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    return new_rating


def get_ratings_by_store(db: Session, store_id: int) -> List[models.StoreRating]:
    return db.query(models.StoreRating).filter(
        models.StoreRating.store_id == store_id
    ).all()


def get_average_rating(db: Session, store_id: int) -> float:
    ratings = get_ratings_by_store(db, store_id)
    if not ratings:
        return 0.0
    avg = sum(r.rating for r in ratings) / len(ratings)
    return round(avg, 2)


def delete_store_rating(db: Session, rating_id: int) -> None:
    rating = db.query(models.StoreRating).filter(
        models.StoreRating.id == rating_id
    ).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    db.delete(rating)
    db.commit()