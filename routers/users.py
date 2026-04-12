from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

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
        "is_graduate": current_user.is_graduate
    }

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