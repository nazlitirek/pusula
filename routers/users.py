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

@router.get("/interests")
def get_interests(db: Session = Depends(get_db)):
    interests = db.query(models.Interest).all()
    return interests