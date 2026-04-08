from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Mentor müsaitlik ekle
@router.post("/availability")
def add_availability(day: str, start_time: str, end_time: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["mentor", "both"]:
        raise HTTPException(status_code=403, detail="Sadece mentorlar müsaitlik ekleyebilir")
    
    availability = models.Availability(
        mentor_id=current_user.id,
        day=day,
        start_time=start_time,
        end_time=end_time
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability

# Mentor müsaitliklerini getir
@router.get("/availability/{mentor_id}")
def get_availability(mentor_id: int, db: Session = Depends(get_db)):
    availability = db.query(models.Availability).filter(models.Availability.mentor_id == mentor_id).all()
    return availability

# Toplantı talebi gönder
@router.post("/request")
def send_meeting_request(mentor_id: int, availability_id: int, meeting_time: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # İlgi alanı kontrolü
    interests = db.query(models.UserInterest).filter(models.UserInterest.user_id == current_user.id).all()
    if not interests:
        raise HTTPException(status_code=400, detail="Önce ilgi alanı seçmelisin")
    
    meeting_request = models.MeetingRequest(
        mentee_id=current_user.id,
        mentor_id=mentor_id,
        availability_id=availability_id,
        meeting_time=datetime.fromisoformat(meeting_time),
        status="pending"
    )
    db.add(meeting_request)
    db.commit()
    db.refresh(meeting_request)
    return meeting_request

# Gelen talepleri getir (mentor için)
@router.get("/incoming")
def get_incoming_requests(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    requests = db.query(models.MeetingRequest).filter(models.MeetingRequest.mentor_id == current_user.id).all()
    return requests

# Giden talepleri getir (mentee için)
@router.get("/outgoing")
def get_outgoing_requests(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    requests = db.query(models.MeetingRequest).filter(models.MeetingRequest.mentee_id == current_user.id).all()
    return requests

# Talebi onayla veya reddet
@router.put("/request/{request_id}")
def update_request_status(request_id: int, status: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if status not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Geçersiz durum")
    
    request = db.query(models.MeetingRequest).filter(models.MeetingRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    
    if request.mentor_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=403, detail="Bu talebi onaylama yetkiniz yok")

    db.query(models.MeetingRequest).filter(
        models.MeetingRequest.id == request_id
    ).update({"status": status}, synchronize_session=False)
    
    db.commit()
    return {"message": f"Talep {status} olarak güncellendi"}