from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from routers.auth import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])

SECRET_KEY = "pusula_secret_key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Geçersiz token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user

@router.get("/me")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "class_year": current_user.class_year,
        "is_graduate": current_user.is_graduate,
        "bio": current_user.bio,
    }

@router.put("/me")
def update_profile(name: Optional[str] = None, class_year: Optional[str] = None, bio: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    update_data = {}
    if name is not None and name.strip():
        update_data["name"] = name
    if class_year is not None and class_year.strip():
        update_data["class_year"] = class_year
    if bio is not None:
        update_data["bio"] = bio.strip()
    
    if update_data:
        db.query(models.User).filter(models.User.id == current_user.id).update(update_data, synchronize_session=False)
        db.commit()
    
    return {"message": "Profil güncellendi!"}

@router.get("/profile/{user_id}")
def get_user_profile(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    user_interests = db.query(models.UserInterest).filter(
        models.UserInterest.user_id == user_id
    ).all()
    
    interest_ids = [ui.interest_id for ui in user_interests]
    interests = db.query(models.Interest).filter(
        models.Interest.id.in_(interest_ids)  # type: ignore
    ).all()
    
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "class_year": user.class_year,
        "is_graduate": user.is_graduate,
        "bio": user.bio,
        "interests": [{"id": i.id, "name": i.name} for i in interests]
    }
@router.get("/interests")
def get_interests(db: Session = Depends(get_db)):
    interests = db.query(models.Interest).all()
    return interests

@router.post("/interests")
def add_interests(interest_ids: list[int], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Önce mevcut ilgi alanlarını sil
    db.query(models.UserInterest).filter(models.UserInterest.user_id == current_user.id).delete()
    
    # Yeni ilgi alanlarını ekle
    for interest_id in interest_ids:
        user_interest = models.UserInterest(user_id=current_user.id, interest_id=interest_id)
        db.add(user_interest)
    
    db.commit()
    return {"message": "İlgi alanları güncellendi!"}

@router.get("/my-interests")
def get_my_interests(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    interests = db.query(models.UserInterest).filter(models.UserInterest.user_id == current_user.id).all()
    return interests

@router.get("/mentor/{mentor_id}")
def get_mentor(mentor_id: int, db: Session = Depends(get_db)):
    mentor = db.query(models.User).filter(models.User.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor bulunamadı")
    return {
        "id": mentor.id,
        "name": mentor.name,
        "role": mentor.role,
        "class_year": mentor.class_year,
        "is_graduate": mentor.is_graduate
    }

@router.get("/mentors")
def get_all_mentors(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    mentors = db.query(models.User).filter(
        models.User.role.in_(["mentor", "both"]),  # type: ignore
        models.User.id != current_user.id
    ).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "role": m.role,
            "class_year": m.class_year,
            "is_graduate": m.is_graduate
        }
        for m in mentors
    ]

@router.put("/change-password")
def change_password(old_password: str, new_password: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not verify_password(old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Mevcut şifre hatalı")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Yeni şifre en az 6 karakter olmalı")
    
    hashed = hash_password(new_password)
    db.query(models.User).filter(models.User.id == current_user.id).update(
        {"password": hashed}, synchronize_session=False
    )
    db.commit()
    return {"message": "Şifre güncellendi!"}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    total_matches = db.query(models.Match).filter(
        (models.Match.mentee_id == current_user.id) |  # type: ignore
        (models.Match.mentor_id == current_user.id)
    ).count()

    total_meetings = db.query(models.MeetingRequest).filter(
        (models.MeetingRequest.mentee_id == current_user.id) |  # type: ignore
        (models.MeetingRequest.mentor_id == current_user.id),
        models.MeetingRequest.status == "accepted"
    ).count()

    return {
        "total_matches": total_matches,
        "total_meetings": total_meetings
    }

@router.get("/my-interests/details")
def get_my_interest_details(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user_interests = db.query(models.UserInterest).filter(
        models.UserInterest.user_id == current_user.id
    ).all()
    
    interest_ids = [ui.interest_id for ui in user_interests]
    interests = db.query(models.Interest).filter(
        models.Interest.id.in_(interest_ids)  # type: ignore
    ).all()
    
    return [{"id": i.id, "name": i.name} for i in interests]