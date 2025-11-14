import os
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents
from schemas import Admission

app = FastAPI(title="College Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- Utilities ---------

def serialize_doc(doc: dict):
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        from datetime import date as _date, datetime as _datetime
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, (_datetime, _date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def ensure_default_admin():
    if db is None:
        return
    existing = db["adminuser"].find_one({})
    if not existing:
        db["adminuser"].insert_one({
            "name": "Default Admin",
            "email": "admin@college.edu",
            "password": "admin123",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })


ensure_default_admin()


# --------- Info Pages (About, Contact) ---------

@app.get("/api/info/about")
async def about_info():
    return {
        "name": "Blue Ridge College",
        "tagline": "Learn. Grow. Lead.",
        "mission": "To provide world-class education and foster innovation.",
        "established": 1995,
        "programs": ["Computer Science", "Business Administration", "Psychology", "Engineering"],
    }


@app.get("/api/info/contact")
async def contact_info():
    return {
        "address": "123 College Ave, Springfield, USA",
        "email": "admissions@college.edu",
        "phone": "+1 (555) 123-4567",
        "office_hours": "Mon-Fri 9:00 AM - 5:00 PM",
    }


# --------- Auth ---------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    user = db["adminuser"].find_one({"email": req.email, "password": req.password, "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_s = serialize_doc(user)
    return {"message": "Login successful", "user": {"id": user_s["id"], "name": user_s.get("name"), "email": user_s.get("email"), "role": user_s.get("role", "admin")}}


# --------- Admissions ---------

@app.post("/api/admissions")
async def submit_admission(admission: Admission):
    try:
        new_id = create_document("admission", admission)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"message": "Application submitted", "id": new_id}


@app.get("/api/admissions")
async def list_admissions(status: Optional[str] = None):
    filt = {"status": status} if status else {}
    try:
        docs = get_documents("admission", filt)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return [serialize_doc(d) for d in docs]


@app.post("/api/admissions/{admission_id}/accept")
async def accept_admission(admission_id: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    # import ObjectId lazily to avoid import errors at startup
    try:
        from bson.objectid import ObjectId
        oid = ObjectId(admission_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid admission id")

    admission = db["admission"].find_one({"_id": oid})
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    student_data = {
        "full_name": admission["full_name"],
        "email": admission["email"],
        "program": admission["program"],
        "roll_no": None,
        "year": 1,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db["student"].insert_one(student_data)
    db["admission"].update_one({"_id": oid}, {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}})
    return {"message": "Admission accepted", "student_id": str(res.inserted_id)}


# --------- Students ---------

@app.get("/api/students")
async def list_students():
    try:
        docs = get_documents("student")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return [serialize_doc(d) for d in docs]


# --------- Attendance ---------

class AttendanceRequest(BaseModel):
    student_id: str
    date: date
    status: str = "present"
    note: Optional[str] = None


@app.post("/api/attendance")
async def mark_attendance(req: AttendanceRequest):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        from bson.objectid import ObjectId
        sid = ObjectId(req.student_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid student id")

    student = db["student"].find_one({"_id": sid})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    d = datetime.combine(req.date, datetime.min.time())
    db["attendance"].update_one(
        {"student_id": str(sid), "date": d.date().isoformat()},
        {"$set": {
            "student_id": str(sid),
            "date": d.date().isoformat(),
            "status": req.status,
            "note": req.note,
            "updated_at": datetime.utcnow(),
        }, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"message": "Attendance recorded"}


@app.get("/api/attendance")
async def get_attendance(student_id: Optional[str] = None, on_date: Optional[str] = None):
    filt = {}
    if student_id:
        filt["student_id"] = student_id
    if on_date:
        filt["date"] = on_date
    try:
        docs = get_documents("attendance", filt)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return [serialize_doc(d) for d in docs]


# --------- Health/Test ---------

@app.get("/")
def read_root():
    return {"message": "College Management API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
