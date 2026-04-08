from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

router = APIRouter(prefix="/matching", tags=["matching"])

def get_interest_vector(user_id: int, all_interest_ids: list, db: Session):
    user_interests = db.query(models.UserInterest).filter(
        models.UserInterest.user_id == user_id
    ).all()
    user_interest_ids = [ui.interest_id for ui in user_interests]
    return [1 if i in user_interest_ids else 0 for i in all_interest_ids]

@router.get("/mentors")
def get_mentor_suggestions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Tüm ilgi alanlarını getir
    all_interests = db.query(models.Interest).all()
    all_interest_ids = [i.id for i in all_interests]

    # Mentee'nin vektörü
    mentee_vector = get_interest_vector(int(current_user.id), all_interest_ids, db)  # type: ignore

    # Eğer ilgi alanı seçilmemişse boş döndür
    if sum(mentee_vector) == 0:
        return {"message": "Önce ilgi alanı seçmelisin", "mentors": []}

    # Tüm mentorları getir
    mentors = db.query(models.User).filter(
        models.User.role.in_(["mentor", "both"]),
        models.User.id != current_user.id
    ).all()

    # Her mentor için benzerlik hesapla
    scores = []
    for mentor in mentors:
        mentor_vector = get_interest_vector(int(mentor.id), all_interest_ids, db)  # type: ignore
        if sum(mentor_vector) == 0:
            continue
        similarity = float(cosine_similarity([mentee_vector], [mentor_vector])[0][0])  # type: ignore
        scores.append((mentor, similarity))

    # En yüksek 3 skoru seç
    scores.sort(key=lambda x: x[1], reverse=True)
    top_3 = scores[:3]

    return {
        "mentors": [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role,
                "class_year": m.class_year,
                "is_graduate": m.is_graduate,
                "similarity": round(float(s), 2)
            }
            for m, s in top_3
        ]
    }