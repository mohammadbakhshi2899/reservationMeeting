from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import DBMS, SMS
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel

SECRET_KEY = "8d969eef6ecad3c29a3a629280bbf9cf5b7e7c0bde4b5f0b1d5e8c8a1f8b5a3f"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # مدت اعتبار توکن

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")


# مدل داده‌ها
class Admin(BaseModel):
    username: str
    password: str

# اطلاعات ادمین (برای مثال، می‌توانید این اطلاعات را از دیتابیس بخوانید)
fake_admin_db = {
    "admin": {
        "username": "admin",
        "password": "admin123",  # رمز عبور ادمین
    }
}

# ایجاد توکن JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# اعتبارسنجی توکن
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

from fastapi import Header, HTTPException

async def get_current_admin(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبارسنجی ناموفق",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # خواندن توکن از کوکی
        token = request.cookies.get("access_token")
        if not token:
            raise credentials_exception

        if token.startswith("Bearer "):
            token = token[9:-1]

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

    except jwt.PyJWTError:
        raise credentials_exception

    # بررسی وجود ادمین در دیتابیس
    admin = fake_admin_db.get(username)
    if admin is None:
        raise credentials_exception
    return admin
# لاگین ادمین و صدور توکن
from fastapi.responses import RedirectResponse

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # بررسی اعتبار نام کاربری و رمز عبور
    admin = fake_admin_db.get(form_data.username)
    if not admin or admin["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # صدور توکن JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin["username"]}, expires_delta=access_token_expires
    )

    # هدایت به صفحه داشبورد مدیریت
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/reserve", response_class=HTMLResponse)
async def reserve_page(request: Request):
    consultants = DBMS.get_all_consultants()
    return templates.TemplateResponse("reserve_form.html", {"request": request, "consultant" : consultants})

@app.post("/reserve")
async def reserve(
        date: str = Form(...),
        time: str = Form(...),
        duration: int = Form(...),
        room_number: str = Form(...),
        owner_name: str = Form(...),
        owner_phone: str = Form(...),
        description: str = Form(...),
        consultant_name: str = Form(...),
        buyer: str = Form(...),
        buyer_phone: str = Form(...)
):
    consultants_id = consultant_name
    consultant_name = DBMS.get_consultant(int(consultants_id))
    if room_number == "اتاق شماره یک":
        room_number = 1
    else:
        room_number = 2
    if not DBMS.is_time_slot_available(date, room_number, time, duration):
        return  RedirectResponse(url="/reserve/failed", status_code=status.HTTP_303_SEE_OTHER)

    DBMS.set_reservation(date, time, duration, owner_name, owner_phone, description, consultant_name, buyer, buyer_phone, room_number, consultants_id)
    SMS.sendMessages(buyer, buyer_phone,owner_name, owner_phone,date, time,  consultants_id)

    return RedirectResponse(url="/reserve/success", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/reserve/failed", response_class=HTMLResponse)
async def reserve_page(request: Request):
    return templates.TemplateResponse("failed_reserve.html", {"request": request})
@app.get("/reserve/success", response_class=HTMLResponse)
async def reserve_success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin_login_user_pass.html", {"request": request})

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_admin: dict = Depends(get_current_admin)):
    # بررسی اینکه کاربر ادمین است
    if current_admin["username"] == "admin":
        reservations = DBMS.get_all_reservation()
        reservations = enumerate(reservations)
        return templates.TemplateResponse(
            "adminDashboard.html",
            {"request": request, "reservations": reservations}
        )
    else:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

@app.get("/admin/edit/{session_id}", response_class=HTMLResponse)
async def edit_session_page(request: Request, session_id: int, current_admin: dict = Depends(get_current_admin)):
    if current_admin["username"] == "admin":
        session = DBMS.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جلسه یافت نشد.")
        return templates.TemplateResponse("edit_session.html", {"request": request, "session": session, "session_id": session_id})
    else:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

@app.post("/admin/edit/{session_id}",)
async def edit_session(
    session_id: int,
    date: str = Form(...),
    room_number : str = Form(...),
    time: str = Form(...),
    duration: int = Form(...),
    buyer_name: str = Form(...),
    buyer_phone: str = Form(...),
    owner_phone: str = Form(...),
    owner_name: str = Form(...),
    description: str = Form(...),
    consultant_name: str = Form(...),
    current_admin: dict = Depends(get_current_admin)
):
    if current_admin["username"] == "admin":
        if room_number == "اتاق شماره یک":
            room_number = 1
        else:
            room_number = 2
        DBMS.eddit_session(date, time, duration, buyer_name, buyer_phone, description, consultant_name, session_id, room_number, owner_name, owner_phone)
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

@app.post("/admin/cancel/{session_id}", response_class=HTMLResponse)
async def cancel_reservation(session_id: int, request: Request, current_admin: dict = Depends(get_current_admin)):
    if current_admin["username"] == "admin":
        DBMS.delete_session(session_id)
        return templates.TemplateResponse("deleted_reservation.html", {"request": request})
    else:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")


@app.get("/admin/view/{session_id}", response_class=HTMLResponse)
async def view_session(request: Request, session_id: int, current_admin: dict = Depends(get_current_admin)):
    if current_admin["username"] == "admin":
        session = DBMS.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="جلسه یافت نشد.")
        session_data = {
            "id": session[0],
            "date": session[1],
            "time": session[2],
            "room_number": session[4],
            "buyer_name": session[5],
            "buyer_phone": session[6],
            "consultant_name": session[7],
            "owner_name": session[9],
            "owner_phone": session[8],
            "description": session[10],
            "duration": session[3]
        }
        return templates.TemplateResponse("view_session.html", {"request": request, "session": session_data})
    else:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

@app.get("/")
def read_root(request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse("main.html", {"request": request})

