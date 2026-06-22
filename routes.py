"""
routes.py
=========
FastAPI routes for: Online Medical Store & Rx Screening

Sections:
  1.  Auth
  2.  Customer Registration (Unified — new)
  3.  User
  4.  Customer
  5.  Profile
  6.  Medical Store + Nearby + Chain Filter (new)
  7.  Medicine
  8.  Medicine Batch
  9.  Prescription + Status Update (new)
  10. Prescription Medicine
  11. PHR (Personal Health Record)
  12. Contraindication + Drug Safety Check  [BUG FIXED: schemas.BaseModel → BaseModel]
  13. MedList
  14. Order  [BUG FIXED: OrderItemCreate order_id removed]
  15. Order Items
  16. Store Rating

BUGS FIXED:
  - SafetyCheckRequest: `schemas.BaseModel` → `BaseModel` (was causing crash)
  - OrderWithItemsRequest items: `OrderItemCreate` ab order_id expect nahi karta
"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel  # <-- correct import (schemas.BaseModel nahi hota)
from sqlalchemy.orm import Session

import controllers
import schemas
from database import get_db

router = APIRouter()


# =====================================================================
# 1. AUTH
# =====================================================================
@router.post("/login", tags=["Auth"])
def login(email: str, password: str, db: Session = Depends(get_db)):
    """Email aur password se login karo, JWT token milega."""
    user = controllers.authenticate_user(db, email, password)
    token = controllers.create_access_token({"sub": str(user.Id), "role": user.Role})
    return {"access_token": token, "token_type": "bearer"}


# =====================================================================
# 2. CUSTOMER REGISTRATION  (Unified — User + Customer ek call mein)
# =====================================================================
@router.post("/register", tags=["Auth"])
def register_customer(data: schemas.CustomerRegister, db: Session = Depends(get_db)):
    """
    Mobile app registration: ek POST call mein User + Customer dono banta hai.
    Pehle wali approach (2 separate calls) ab optional reh gayi.
    """
    return controllers.register_customer(db, data)


# =====================================================================
# 3. USER
# =====================================================================
@router.post("/users", tags=["User"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Naya user banao (manual — SuperAdmin ke liye)."""
    return controllers.create_user(db, user)


@router.get("/users", tags=["User"])
def get_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Sab users ki list lo."""
    return controllers.get_all_users(db, skip, limit)


@router.get("/users/{user_id}", tags=["User"])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Ek user ID se nikalo."""
    return controllers.get_user(db, user_id)


@router.delete("/users/{user_id}", tags=["User"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """User delete karo."""
    controllers.delete_user(db, user_id)
    return {"message": "User delete ho gaya"}


# =====================================================================
# 4. CUSTOMER
# =====================================================================
@router.post("/customers", tags=["Customer"])
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    """Naya customer banao (pehle linked user hona chahiye)."""
    return controllers.create_customer(db, customer)


@router.get("/customers", tags=["Customer"])
def get_all_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Sab customers ki list lo."""
    return controllers.get_all_customers(db, skip, limit)


@router.get("/customers/{c_id}", tags=["Customer"])
def get_customer(c_id: int, db: Session = Depends(get_db)):
    """Ek customer ID se nikalo."""
    return controllers.get_customer(db, c_id)


@router.put("/customers/{c_id}", tags=["Customer"])
def update_customer(c_id: int, customer: schemas.CustomerBase, db: Session = Depends(get_db)):
    """Customer ki info update karo."""
    return controllers.update_customer(db, c_id, customer)


@router.delete("/customers/{c_id}", tags=["Customer"])
def delete_customer(c_id: int, db: Session = Depends(get_db)):
    """Customer delete karo."""
    controllers.delete_customer(db, c_id)
    return {"message": "Customer delete ho gaya"}


# =====================================================================
# 5. PROFILE
# =====================================================================
@router.post("/profiles", tags=["Profile"])
def create_profile(profile: schemas.ProfileCreate, db: Session = Depends(get_db)):
    """Customer ka naya profile banao (family member bhi ho sakta hai)."""
    return controllers.create_profile(db, profile)


@router.get("/profiles/{profile_id}", tags=["Profile"])
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Profile ID se nikalo."""
    return controllers.get_profile(db, profile_id)


@router.get("/customers/{cus_id}/profiles", tags=["Profile"])
def get_profiles_by_customer(cus_id: int, db: Session = Depends(get_db)):
    """Customer ke sab active profiles lo."""
    return controllers.get_profiles_by_customer(db, cus_id)


@router.put("/profiles/{profile_id}", tags=["Profile"])
def update_profile(profile_id: int, profile: schemas.ProfileBase, db: Session = Depends(get_db)):
    """Profile update karo."""
    return controllers.update_profile(db, profile_id, profile)


@router.delete("/profiles/{profile_id}", tags=["Profile"])
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    """Profile soft delete karo (inactive ho jaye gi)."""
    controllers.delete_profile(db, profile_id)
    return {"message": "Profile inactive ho gayi"}


# =====================================================================
# 6. MEDICAL STORE
# =====================================================================
@router.post("/stores", tags=["Medical Store"])
def create_store(store: schemas.MedicalStoreCreate, db: Session = Depends(get_db)):
    """Naya medical store banao."""
    return controllers.create_medicalstore(db, store)


@router.get("/stores", tags=["Medical Store"])
def get_all_stores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Sab stores ki list lo."""
    return controllers.get_all_medicalstores(db, skip, limit)


@router.get("/stores/nearby", tags=["Medical Store"])
def get_nearby_stores(
    lat: float,
    long: float,
    radius_km: float = 10.0,
    chain_name: str = None,
    db: Session = Depends(get_db),
):
    """
    Customer ke GPS se nearest branches dhundho.
    Optional: chain_name se filter karo (e.g. 'Shaheen Chemist').
    Example: GET /stores/nearby?lat=33.69&long=73.05&radius_km=5
    """
    return controllers.get_nearby_stores(db, lat, long, radius_km, chain_name)


@router.get("/stores/chains", tags=["Medical Store"])
def get_all_chain_names(db: Session = Depends(get_db)):
    """
    Database mein jitni bhi pharmacy chains hain unke unique names lo.
    Frontend dropdown populate karne ke liye.
    Example: GET /stores/chains
    """
    return controllers.get_all_chain_names(db)


@router.get("/stores/by-chain/{chain_name}", tags=["Medical Store"])
def get_stores_by_chain(chain_name: str, db: Session = Depends(get_db)):
    """
    Ek pharmacy chain ki sab branches lo.
    Example: GET /stores/by-chain/Shaheen Chemist
    """
    return controllers.get_stores_by_chain(db, chain_name)


@router.get("/stores/{store_id}", tags=["Medical Store"])
def get_store(store_id: int, db: Session = Depends(get_db)):
    """Ek store ID se nikalo."""
    return controllers.get_medicalstore(db, store_id)


@router.put("/stores/{store_id}", tags=["Medical Store"])
def update_store(store_id: int, store: schemas.MedicalStoreBase, db: Session = Depends(get_db)):
    """Store info update karo."""
    return controllers.update_medicalstore(db, store_id, store)


@router.delete("/stores/{store_id}", tags=["Medical Store"])
def delete_store(store_id: int, db: Session = Depends(get_db)):
    """Store delete karo."""
    controllers.delete_medicalstore(db, store_id)
    return {"message": "Store delete ho gaya"}


# =====================================================================
# 7. MEDICINE
# =====================================================================
@router.post("/medicines", tags=["Medicine"])
def create_medicine(medicine: schemas.MedicineCreate, db: Session = Depends(get_db)):
    """Store mein nai medicine add karo."""
    return controllers.create_medicine(db, medicine)


@router.get("/stores/{store_id}/medicines", tags=["Medicine"])
def get_medicines_by_store(store_id: int, db: Session = Depends(get_db)):
    """Store ki sab medicines lo."""
    return controllers.get_medicines_by_store(db, store_id)


@router.get("/medicines/search", tags=["Medicine"])
def search_medicines(query: str, db: Session = Depends(get_db)):
    """Medicine name ya base name se search karo."""
    return controllers.search_medicines(db, query)


@router.get("/medicines/{med_id}", tags=["Medicine"])
def get_medicine(med_id: int, db: Session = Depends(get_db)):
    """Ek medicine ID se nikalo."""
    return controllers.get_medicine(db, med_id)


@router.put("/medicines/{med_id}", tags=["Medicine"])
def update_medicine(med_id: int, medicine: schemas.MedicineBase, db: Session = Depends(get_db)):
    """Medicine info update karo."""
    return controllers.update_medicine(db, med_id, medicine)


@router.delete("/medicines/{med_id}", tags=["Medicine"])
def delete_medicine(med_id: int, db: Session = Depends(get_db)):
    """Medicine delete karo."""
    controllers.delete_medicine(db, med_id)
    return {"message": "Medicine delete ho gayi"}


# =====================================================================
# 8. MEDICINE BATCH
# =====================================================================
@router.post("/medicine-batches", tags=["Medicine Batch"])
def create_batch(batch: schemas.MedicineBatchCreate, db: Session = Depends(get_db)):
    """Medicine ka naya batch add karo."""
    return controllers.create_medicine_batch(db, batch)


@router.get("/medicine-batches/{batch_id}", tags=["Medicine Batch"])
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    """Batch ID se nikalo."""
    return controllers.get_medicine_batch(db, batch_id)


@router.get("/medicines/{med_id}/batches", tags=["Medicine Batch"])
def get_batches_by_medicine(med_id: int, db: Session = Depends(get_db)):
    """Medicine ke sab batches lo (FEFO order mein)."""
    return controllers.get_batches_by_medicine(db, med_id)


@router.get("/medicines/{med_id}/stock", tags=["Medicine Batch"])
def get_total_stock(med_id: int, db: Session = Depends(get_db)):
    """Medicine ka total available stock lo."""
    total = controllers.get_total_stock(db, med_id)
    return {"med_id": med_id, "total_stock": total}


@router.delete("/medicine-batches/{batch_id}", tags=["Medicine Batch"])
def delete_batch(batch_id: int, db: Session = Depends(get_db)):
    """Batch delete karo."""
    controllers.delete_medicine_batch(db, batch_id)
    return {"message": "Batch delete ho gayi"}


# =====================================================================
# 9. PRESCRIPTION
# =====================================================================
@router.post("/prescriptions", tags=["Prescription"])
def create_prescription(prescription: schemas.PrescriptionCreate, db: Session = Depends(get_db)):
    """Nai prescription upload karo."""
    return controllers.create_prescription(db, prescription)


@router.get("/prescriptions/{prescription_id}", tags=["Prescription"])
def get_prescription(prescription_id: int, db: Session = Depends(get_db)):
    """Prescription ID se nikalo."""
    return controllers.get_prescription(db, prescription_id)


@router.get("/customers/{cust_id}/prescriptions", tags=["Prescription"])
def get_prescriptions_by_customer(cust_id: int, db: Session = Depends(get_db)):
    """Customer ki sab prescriptions lo."""
    return controllers.get_prescriptions_by_customer(db, cust_id)


@router.patch("/prescriptions/{prescription_id}/status", tags=["Prescription"])
def update_prescription_status(
    prescription_id: int,
    body: schemas.PrescriptionStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Staff ke liye: prescription approve ya reject karo.
    Valid values: 'Approved', 'Rejected'
    Body: { "status": "Approved" }
    """
    return controllers.update_prescription_status(db, prescription_id, body.status)


@router.delete("/prescriptions/{prescription_id}", tags=["Prescription"])
def delete_prescription(prescription_id: int, db: Session = Depends(get_db)):
    """Prescription delete karo."""
    controllers.delete_prescription(db, prescription_id)
    return {"message": "Prescription delete ho gayi"}


# =====================================================================
# 10. PRESCRIPTION MEDICINE
# =====================================================================
@router.post("/prescription-medicines", tags=["Prescription Medicine"])
def create_prescription_medicine(pm: schemas.PrescriptionMedicineCreate, db: Session = Depends(get_db)):
    """Prescription mein medicine entry add karo."""
    return controllers.create_prescription_medicine(db, pm)


@router.get("/prescriptions/{prescription_id}/medicines", tags=["Prescription Medicine"])
def get_prescription_medicines(prescription_id: int, db: Session = Depends(get_db)):
    """Prescription ki sab medicines lo."""
    return controllers.get_prescription_medicines(db, prescription_id)


@router.delete("/prescription-medicines/{pm_id}", tags=["Prescription Medicine"])
def delete_prescription_medicine(pm_id: int, db: Session = Depends(get_db)):
    """Prescription medicine entry delete karo."""
    controllers.delete_prescription_medicine(db, pm_id)
    return {"message": "Entry delete ho gayi"}


# =====================================================================
# 11. PHR (Personal Health Record)
# =====================================================================
@router.post("/phr", tags=["PHR"])
def create_phr_entry(phr: schemas.PHRCreate, db: Session = Depends(get_db)):
    """Profile mein nai health entry add karo (bimari ya current medicine)."""
    return controllers.create_phr_entry(db, phr)


@router.get("/profiles/{profile_id}/phr", tags=["PHR"])
def get_phr_by_profile(profile_id: int, db: Session = Depends(get_db)):
    """Profile ki sab PHR entries lo."""
    return controllers.get_phr_by_profile(db, profile_id)


@router.delete("/phr/{phr_id}", tags=["PHR"])
def delete_phr_entry(phr_id: int, db: Session = Depends(get_db)):
    """PHR entry delete karo."""
    controllers.delete_phr_entry(db, phr_id)
    return {"message": "PHR entry delete ho gayi"}


# =====================================================================
# 12. CONTRAINDICATION + DRUG SAFETY CHECK
# =====================================================================
@router.post("/contraindications", tags=["Contraindication"])
def create_contraindication(rule: schemas.ContraindicationCreate, db: Session = Depends(get_db)):
    """Naya contraindication rule add karo (admin kare ga)."""
    return controllers.create_contraindication(db, rule)


@router.get("/contraindications", tags=["Contraindication"])
def get_all_contraindications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Sab contraindication rules lo."""
    return controllers.get_all_contraindications(db, skip, limit)


@router.delete("/contraindications/{rule_id}", tags=["Contraindication"])
def delete_contraindication(rule_id: int, db: Session = Depends(get_db)):
    """Contraindication rule delete karo."""
    controllers.delete_contraindication(db, rule_id)
    return {"message": "Rule delete ho gaya"}


# BUG FIX: pehle yahan `schemas.BaseModel` likha tha jo crash karta tha.
# `BaseModel` ko file ke upar se `pydantic` se import kiya gaya hai.
class SafetyCheckRequest(BaseModel):
    profile_id: int
    med_ids: List[int]


@router.post("/safety-check", tags=["Contraindication"])
def check_medicine_safety(request: SafetyCheckRequest, db: Session = Depends(get_db)):
    """
    Order se pehle drug safety check karo.
    Profile ki health history aur cart medicines check hoti hain.
    Warnings return hoti hain — customer decide kare proceed kare ya nahi.
    """
    warnings = controllers.check_medicine_safety(db, request.profile_id, request.med_ids)
    if not warnings:
        return {"safe": True, "message": "Koi contraindication nahi mila", "warnings": []}
    return {"safe": False, "message": "Kuch warnings hain, zaroor check karo", "warnings": warnings}


# =====================================================================
# 13. MEDLIST
# =====================================================================
@router.post("/medlist", tags=["MedList"])
def create_medlist_entry(entry: schemas.MedListCreate, db: Session = Depends(get_db)):
    """MedList mein nai entry add karo."""
    return controllers.create_medlist_entry(db, entry)


@router.get("/medlist", tags=["MedList"])
def get_all_medlist(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Poori medlist lo."""
    return controllers.get_all_medlist(db, skip, limit)


@router.get("/medlist/search", tags=["MedList"])
def search_medlist(query: str, db: Session = Depends(get_db)):
    """MedList mein medicine name ya base name se search karo."""
    return controllers.search_medlist(db, query)


@router.delete("/medlist/{entry_id}", tags=["MedList"])
def delete_medlist_entry(entry_id: int, db: Session = Depends(get_db)):
    """MedList entry delete karo."""
    controllers.delete_medlist_entry(db, entry_id)
    return {"message": "MedList entry delete ho gayi"}


# =====================================================================
# 14. ORDER
# =====================================================================
# BUG FIX: OrderItemCreate mein ab order_id field nahi — controller set karta hai.
class OrderWithItemsRequest(BaseModel):
    order: schemas.OrderCreate
    items: List[schemas.OrderItemCreate]


@router.post("/orders", tags=["Order"])
def create_order(request: OrderWithItemsRequest, db: Session = Depends(get_db)):
    """
    Naya order banao — order + sab items ek saath.
    Stock automatically FEFO se deduct hoga.
    prescription_id optional hai (Rx wali medicines ke liye).

    Body example:
    {
      "order": {
        "cust_id": 1,
        "profile_id": 1,
        "store_id": 6,
        "prescription_id": 1,
        "total_amount": 320.00
      },
      "items": [
        {"med_id": 1, "quantity": 1, "unit_price": 120.00},
        {"med_id": 2, "quantity": 1, "unit_price": 200.00}
      ]
    }
    """
    return controllers.create_order(db, request.order, request.items)


@router.get("/orders/{order_id}", tags=["Order"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Order ID se nikalo."""
    return controllers.get_order(db, order_id)


@router.get("/customers/{cust_id}/orders", tags=["Order"])
def get_orders_by_customer(cust_id: int, db: Session = Depends(get_db)):
    """Customer ke sab orders lo."""
    return controllers.get_orders_by_customer(db, cust_id)


@router.get("/stores/{store_id}/orders", tags=["Order"])
def get_orders_by_store(store_id: int, db: Session = Depends(get_db)):
    """Store ke sab orders lo."""
    return controllers.get_orders_by_store(db, store_id)


@router.patch("/orders/{order_id}/status", tags=["Order"])
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    """
    Order ka status update karo.
    Valid statuses: Pending, Prescription Verified, Ready for Pickup, Completed, Rejected
    """
    return controllers.update_order_status(db, order_id, status)


@router.delete("/orders/{order_id}", tags=["Order"])
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Order delete karo."""
    controllers.delete_order(db, order_id)
    return {"message": "Order delete ho gaya"}


# =====================================================================
# 15. ORDER ITEMS
# =====================================================================
@router.get("/orders/{order_id}/items", tags=["Order Items"])
def get_order_items(order_id: int, db: Session = Depends(get_db)):
    """Order ke sab items lo."""
    return controllers.get_order_items(db, order_id)


@router.delete("/order-items/{item_id}", tags=["Order Items"])
def delete_order_item(item_id: int, db: Session = Depends(get_db)):
    """Order item delete karo."""
    controllers.delete_order_item(db, item_id)
    return {"message": "Order item delete ho gaya"}


# =====================================================================
# 16. STORE RATING
# =====================================================================
@router.post("/store-ratings", tags=["Store Rating"])
def create_store_rating(rating: schemas.StoreRatingCreate, db: Session = Depends(get_db)):
    """Store ko rating do."""
    return controllers.create_store_rating(db, rating)


@router.get("/stores/{store_id}/ratings", tags=["Store Rating"])
def get_ratings_by_store(store_id: int, db: Session = Depends(get_db)):
    """Store ki sab ratings lo."""
    return controllers.get_ratings_by_store(db, store_id)


@router.get("/stores/{store_id}/average-rating", tags=["Store Rating"])
def get_average_rating(store_id: int, db: Session = Depends(get_db)):
    """Store ki average rating lo."""
    avg = controllers.get_average_rating(db, store_id)
    return {"store_id": store_id, "average_rating": avg}


@router.delete("/store-ratings/{rating_id}", tags=["Store Rating"])
def delete_store_rating(rating_id: int, db: Session = Depends(get_db)):
    """Rating delete karo."""
    controllers.delete_store_rating(db, rating_id)
    return {"message": "Rating delete ho gayi"}