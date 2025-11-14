"""
Database Schemas for College App

Each Pydantic model maps to a MongoDB collection with the lowercase class name.
Examples:
- AdminUser -> "adminuser"
- Student -> "student"
- Admission -> "admission"
- Attendance -> "attendance"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
import datetime as dt


class AdminUser(BaseModel):
    """Admin users who can log in to manage admissions and attendance"""
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address (unique)")
    password: str = Field(..., min_length=6, description="Password (hashed in production)")
    role: Literal["admin", "staff"] = Field("admin", description="User role")
    is_active: bool = Field(True, description="Active status")


class Admission(BaseModel):
    """Admission application submitted by prospective students"""
    full_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    address: str = Field(...)
    program: str = Field(..., description="Program applied for")
    dob: dt.date = Field(..., description="Date of birth")
    previous_education: Optional[str] = Field(None)
    status: Literal["pending", "accepted", "rejected"] = Field("pending")


class Student(BaseModel):
    """Student record"""
    full_name: str = Field(...)
    email: EmailStr = Field(...)
    program: str = Field(...)
    roll_no: Optional[str] = Field(None, description="Roll number")
    year: Optional[int] = Field(None, ge=1, le=6)
    is_active: bool = Field(True)


class Attendance(BaseModel):
    """Attendance entry for a student on a specific date"""
    student_id: str = Field(..., description="ObjectId as string of the student")
    on_date: dt.date = Field(..., description="Attendance date")
    status: Literal["present", "absent", "late"] = Field("present")
    note: Optional[str] = None
