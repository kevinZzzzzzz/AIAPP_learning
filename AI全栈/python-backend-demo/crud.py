from sqlalchemy.orm import Session
import models, schemas

# === Users CRUD ===
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.UserModel).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.UserModel).filter(models.UserModel.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.UserModel(
        username=user.username,
        nickname=user.nickname,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

# === Appointments CRUD ===
def get_appointments(db: Session, user_id: int = None):
    query = db.query(models.AppointmentModel)
    if user_id:
        query = query.filter(models.AppointmentModel.user_id == user_id)
    return query.all()

def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    db_appt = models.AppointmentModel(
        user_id=appointment.user_id,
        title=appointment.title,
        description=appointment.description,
        status=appointment.status
    )
    db.add(db_appt)
    db.commit()
    db.refresh(db_appt)
    return db_appt
