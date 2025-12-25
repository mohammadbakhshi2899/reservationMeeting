import sqlite3
# import SMS

conn = sqlite3.connect("reservations.db", check_same_thread=False)
cursor = conn.cursor()

def check_reservation(date, time):
    return True
    cursor.execute("SELECT COUNT(*) FROM reservations WHERE ddate = ? AND ttime = ?", (date, time))
    count = cursor.fetchone()[0]
    if count >= 2:
        return False
    return True

def set_reservation(date, time, duration, owner_name, owner_phone, description, consultant_name, buyer, buyer_phone, room_number, consultant_id):
      # تبدیل ساعت شروع به دقیقه (برای محاسبات)
    start_hour, start_minute = map(int, time.split(":"))
    start_minute_total = start_hour * 60 + start_minute

    # محاسبه بازه زمانی جلسه
    end_minute_total = start_minute_total + duration

    # لیست تمام بازه‌های نیم‌ساعته در جدول
    time_slots = [
        "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
        "11:00", "11:30", "12:00", "12:30", "13:00",
        "16:00", "16:30", "17:00", "17:30", "18:00",
        "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"
    ]

    # پیدا کردن بازه‌های زمانی مرتبط با جلسه
    overlapping_slots = []
    for slot in time_slots:
        slot_hour, slot_minute = map(int, slot.split(":"))
        slot_minute_total = slot_hour * 60 + slot_minute
        if start_minute_total <= slot_minute_total < end_minute_total:
            overlapping_slots.append(slot)

    set_slot(overlapping_slots, date, room_number, buyer)

    cursor.execute("""
       INSERT INTO reservations (ddate, ttime, duration, owner_name, owner_phone, description, consultant_name, buyer_name, buyer_phone, room_number)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       """, (date, time, duration, owner_name, owner_phone, description, consultant_name , buyer, buyer_phone, room_number))
    conn.commit()

    # SMS.sendMessages(buyer, buyer_phone,owner_name, owner_phone,date, time,  consultant_id)

def get_all_reservation():
    cursor.execute("SELECT * FROM reservations ORDER BY id DESC")
    reservations = cursor.fetchall()
    return reservations

def eddit_session(date, time, duration, buyer_name, buyer_phone, description, consultant_name, session_id, room_number, owner_name, owner_phone):
    cursor.execute("""
        UPDATE reservations
        SET ddate = ?, ttime = ?, duration = ?, buyer_name = ?, buyer_phone = ?, description = ?, consultant_name = ? , room_number = ?, owner_name = ?, owner_phone = ?
        WHERE id = ?
        """, (date, time, duration, buyer_name, buyer_phone, description, consultant_name, room_number, owner_name, owner_phone, session_id))
    conn.commit()

def get_session(session_id):
    cursor.execute("SELECT * FROM reservations WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    return session

def delete_session(session_id):
    cursor.execute("""
       SELECT ddate, room_number, ttime, duration FROM reservations
       WHERE id = ?
       """, (session_id,))
    session = cursor.fetchone()
    if session is None:
        return False

    session_date, session_room_number, start_time, duration = session

    # تبدیل ساعت شروع به دقیقه
    start_hour, start_minute = map(int, start_time.split(":"))
    start_minute_total = start_hour * 60 + start_minute
    end_minute_total = start_minute_total + int(duration)

    # لیست تمام بازه‌های نیم‌ساعته در جدول
    time_slots = [
        "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
        "11:00", "11:30", "12:00", "12:30", "13:00",
        "16:00", "16:30", "17:00", "17:30", "18:00",
        "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"
    ]

    # پیدا کردن بازه‌های زمانی مرتبط با جلسه
    overlapping_slots = []
    for slot in time_slots:
        slot_hour, slot_minute = map(int, slot.split(":"))
        slot_minute_total = slot_hour * 60 + slot_minute
        if start_minute_total <= slot_minute_total < end_minute_total:
            overlapping_slots.append(slot)

    # آزاد کردن بازه‌های زمانی مرتبط در جدول room_schedule
    for slot in overlapping_slots:
        cursor.execute(f"""
           UPDATE room_schedule
           SET "{slot}" = NULL
           WHERE ddate = ? AND room_number = ?
           """, (session_date, session_room_number))
        # room = cursor.execute(f"""
        #         SELECT "{slot}" room_schedule
        #         WHERE ddate = ? AND room_number = ?
        #         """, (session_date, session_room_number))
        # room = room.fetchall()
        # print(room)
        conn.commit()
    cursor.execute("DELETE FROM reservations WHERE id = ?", (session_id,))
    conn.commit()


def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    if not user:
        return False
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
    return user

def is_admin(username):
    cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user or user[0] != "admin":
        return False
    return True

def is_time_slot_available(date, room_number, start_time, duration):
    """
    بررسی می‌کند که آیا بازه زمانی مشخصی برای رزرو در دسترس است یا خیر.

    :param date: تاریخ جلسه (TEXT)
    :param room_number: شماره اتاق جلسه (INTEGER)
    :param start_time: ساعت شروع جلسه (TEXT, فرمت HH:MM)
    :param duration: مدت زمان جلسه به دقیقه (INTEGER)
    :return: True اگر بازه زمانی در دسترس باشد، False در غیر این صورت
    """
    # تبدیل ساعت شروع به دقیقه (برای محاسبات)
    start_hour, start_minute = map(int, start_time.split(":"))
    start_minute_total = start_hour * 60 + start_minute

    # محاسبه بازه زمانی جلسه
    end_minute_total = start_minute_total + duration

    # لیست تمام بازه‌های نیم‌ساعته در جدول
    time_slots = [
        "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
        "11:00", "11:30", "12:00", "12:30", "13:00",
        "16:00", "16:30", "17:00", "17:30", "18:00",
        "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"
    ]

    # پیدا کردن بازه‌های زمانی مرتبط با جلسه
    overlapping_slots = []
    for slot in time_slots:
        slot_hour, slot_minute = map(int, slot.split(":"))
        slot_minute_total = slot_hour * 60 + slot_minute
        if start_minute_total <= slot_minute_total < end_minute_total:
            overlapping_slots.append(slot)

    row = []
    if len(overlapping_slots) > 0:
        for slot in overlapping_slots:
            query = f""" 
                        select "{str(slot)}" from room_schedule where ddate = "{date}" and room_number = "{str(room_number)}"
                    """
            cursor.execute(query)
            chank = cursor.fetchone()
            if chank is not None:
                row.append(chank)

    if row is not None:
        for slot_value in row:
            if slot_value[0] is not None:  #
                # اگر بازه زمانی رزرو شده باشد
                return False
    return True

def set_slot(overlapping_slots,ddate,  room_number, buyer_name):
    for slot in overlapping_slots:
        cursor.execute(f"""
           INSERT OR IGNORE INTO room_schedule (ddate, room_number, "{slot}")
           VALUES (?, ?, ?)
           """, (ddate, room_number, buyer_name))
        cursor.execute(f"""
           UPDATE room_schedule
           SET "{slot}" = ?
           WHERE ddate = ? AND room_number = ?
           """, (buyer_name, ddate, room_number))

    conn.commit()

def get_all_consultants():
    cursor.execute("SELECT id ,name, family FROM Users where role == 'مشاور'")
    consultants = cursor.fetchall()
    return consultants
def get_all_users():
    cursor.execute("SELECT id ,name, family, phone FROM Users")
    users = cursor.fetchall()
    return users
def get_consultant(consultant_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (consultant_id,))
    consultant = cursor.fetchone()
    if not consultant:
        return None
    return str(consultant[1] + " " + consultant[2])

def get_other():
    role = "مدیر قرارداد"
    role1 = "مدیر داخلی"
    role2 = "حسابدار"
    cursor.execute("SELECT * FROM users WHERE role = ? or role = ? or role = ?", (role,role1,role2))
    consultant = cursor.fetchall()
    return consultant

def get_consultant_phone(consultant_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (consultant_id,))
    consultant = cursor.fetchone()
    if not consultant:
        return None
    return consultant[4]

def update_user(consultant_id,consultant_phone, consultant_name, consultant_family):
    cursor.execute("UPDATE Users SET name = ?,  family = ?, phone = ? WHERE id = ?", (consultant_name, consultant_family, consultant_phone, consultant_id))

def delete_user(consultant_id):
    cursor.execute("DELETE FROM users WHERE id = ?", (consultant_id,))
    conn.commit()