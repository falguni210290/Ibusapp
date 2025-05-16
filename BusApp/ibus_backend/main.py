from fastapi import FastAPI, Request,HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import random
import requests
import time

app = FastAPI()

# ✅ Apply CORS middleware at the top (only once)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 👈 your React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Models ----------------
class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str

class LoginRequest(BaseModel):
    phone: str
    password: str

class PhoneOnlyRequest(BaseModel):
    phone: str

class OTPRequest(BaseModel):
    phone: str

class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str

# ---------------- DB Setup ----------------
def get_connection():
    return sqlite3.connect("ibus_users.db")

def create_user_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_otp_table():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_data (
            phone TEXT PRIMARY KEY,
            otp TEXT,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

create_user_table()
create_otp_table()

# ---------------- Routes ----------------

@app.get("/")
def root():
    return {"message": "iBus API running"}

@app.post("/register")
def register_user(request: RegisterRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (request.phone,))
    existing_user = cursor.fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already exists")
    cursor.execute(
        "INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
        (request.name, request.email, request.phone, request.password)
    )
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/login")
def login_user(request: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (request.phone,))
    user = cursor.fetchone()
    conn.close()
    if user and user[4] == request.password:
        return {"message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")

@app.post("/validatephone")
def validate_phone(request: PhoneOnlyRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (request.phone,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"message": "User exists"}
    else:
        raise HTTPException(status_code=404, detail="Phone number not registered")

@app.post("/send-otp")
def send_otp(request: OTPRequest):
    try:
        phone = request.phone
        otp = str(random.randint(100000, 999999))
        timestamp = int(time.time())

        # Save to DB
        DB = "users.db"
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO otp_data (phone, otp, timestamp) VALUES (?, ?, ?)", (phone, otp, timestamp))
        conn.commit()
        conn.close()

        # Fast2SMS sending
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": "QkYEs0HeDjygTtph2J9T3RHHmT0mDwBUOXPkHYbMbcoxQHB3f7jlpx80KioI",  # ⚠️ Replace this
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "message": f"Your OTP is {otp}",
            "route": "q",
            "numbers": phone
        }

        response = requests.post(url, data=payload, headers=headers)
        print("Fast2SMS response:", response.text)  # 👈 Log response

        if response.status_code == 200:
            return {"success": True, "message": "OTP sent"}
        else:
            raise HTTPException(status_code=400, detail=response.text)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify-otp")
def verify_otp(request: OTPVerifyRequest):
    phone = request.phone
    user_otp = request.otp

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT otp, timestamp FROM otp_data WHERE phone=?", (phone,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No OTP found")
    db_otp, timestamp = row
    if int(time.time()) - timestamp > 300:
        raise HTTPException(status_code=400, detail="OTP expired")
    if user_otp == db_otp:
        return {"success": True, "message": "OTP verified"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")
@app.get("/test-cors")
def test_cors():
    return {"status": "ok"}


class PhoneOnlyRequest(BaseModel):
    phone: str

@app.post("/get-user")
def get_user_by_phone(request: PhoneOnlyRequest):
    conn = sqlite3.connect("ibus_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE phone=?", (request.phone,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"name": row[0]}
    else:
        raise HTTPException(status_code=404, detail="User not found")
    

def search_buses(from_place, to_place, date, time):
    conn = sqlite3.connect("ibus.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bus_name, time, price, seats
        FROM buses
        WHERE LOWER(from_place) = ? AND LOWER(to_place) = ? AND date = ? AND time >= ?
    """, (from_place.lower(), to_place.lower(), date, time))
    buses = cursor.fetchall()
    conn.close()
    return buses


@app.post("/search-buses")
async def search_buses_api(request: Request):
    data = await request.json()

    from_place = data.get("from", "")
    to_place = data.get("to", "")
    date = data.get("date", "")
    time = data.get("time", "")

    print(f"🧾 Searching: {from_place} → {to_place} on {date} after {time}")

    buses = search_buses(from_place, to_place, date, time)

    print("🎯 Found:", buses)

    return {
        "buses": [
            {
                "bus_name": bus[0],
                "time": bus[1],
                "price": bus[2],
                "seats": bus[3]
            } for bus in buses
        ]
    }