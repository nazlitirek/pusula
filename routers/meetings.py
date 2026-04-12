from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time
from datetime import date as DateType

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
def get_availability(mentor_id: int, date: str = None, db: Session = Depends(get_db)):
    availabilities = db.query(models.Availability).filter(
        models.Availability.mentor_id == mentor_id
    ).all()
    
    result = []
    for a in availabilities:
        is_booked = False
        if date:
            selected_date = DateType.fromisoformat(date)
            existing = db.query(models.MeetingRequest).filter(
                models.MeetingRequest.availability_id == a.id,
                models.MeetingRequest.meeting_date == selected_date,
                models.MeetingRequest.status.in_(["pending", "accepted"])  # type: ignore
            ).first()
            is_booked = existing is not None
        
        result.append({
            "id": a.id,
            "mentor_id": a.mentor_id,
            "day": a.day,
            "start_time": str(a.start_time),
            "end_time": str(a.end_time),
            "is_booked": is_booked
        })
    
    return result
# Toplantı talebi gönder


@router.post("/request")
def send_meeting_request(mentor_id: int, availability_id: int, meeting_time: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # İlgi alanı kontrolü
    interests = db.query(models.UserInterest).filter(models.UserInterest.user_id == current_user.id).all()
    if not interests:
        raise HTTPException(status_code=400, detail="Önce ilgi alanı seçmelisin")

    meeting_datetime = datetime.fromisoformat(meeting_time)
    meeting_date = meeting_datetime.date()

    # Haftada max 2 toplantı kontrolü
    week_start = meeting_date - timedelta(days=meeting_date.weekday())
    week_end = week_start + timedelta(days=6)
    weekly_requests = db.query(models.MeetingRequest).filter(
        models.MeetingRequest.mentee_id == current_user.id,
        models.MeetingRequest.meeting_date >= week_start,
        models.MeetingRequest.meeting_date <= week_end,
        models.MeetingRequest.status.in_(["pending", "accepted"])  # type: ignore
    ).count()
    if weekly_requests >= 2:
        raise HTTPException(status_code=400, detail="Bu hafta maksimum 2 toplantı talebinde bulunabilirsin")

    # Aynı mentörle 7 gün içinde toplantı kontrolü
    next_7_days = meeting_date + timedelta(days=7)
    existing_with_mentor = db.query(models.MeetingRequest).filter(
        models.MeetingRequest.mentee_id == current_user.id,
        models.MeetingRequest.mentor_id == mentor_id,
        models.MeetingRequest.meeting_date >= meeting_date,
        models.MeetingRequest.meeting_date <= next_7_days,
        models.MeetingRequest.status.in_(["pending", "accepted"])  # type: ignore
    ).first()
    if existing_with_mentor:
        raise HTTPException(status_code=400, detail="Bu mentörle önümüzdeki 7 gün içinde zaten bir toplantınız var")

    # Aynı tarih ve saate çift talep kontrolü
    existing = db.query(models.MeetingRequest).filter(
        models.MeetingRequest.mentor_id == mentor_id,
        models.MeetingRequest.availability_id == availability_id,
        models.MeetingRequest.meeting_date == meeting_date,
        models.MeetingRequest.status.in_(["pending", "accepted"])  # type: ignore
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu saat dolu, lütfen başka bir zaman seçin")

    meeting_request = models.MeetingRequest(
        mentee_id=current_user.id,
        mentor_id=mentor_id,
        availability_id=availability_id,
        meeting_time=meeting_datetime,
        meeting_date=meeting_date,
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