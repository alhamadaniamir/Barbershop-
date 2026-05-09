from flask import Flask, render_template, request, g
import sqlite3
import calendar
from pathlib import Path

DATABASE = Path(__file__).parent / "appointments.db"

app = Flask(__name__)
app.config['DATABASE'] = str(DATABASE)


# Shared site data
TEAM_MEMBERS = [
    {
        "id": 1,
        "name": "Francis",
        "role": "Owner & Master Barber",
        "bio": "20+ years of barbering excellence. Specializes in classic cuts, fades, and traditional shaves. Francis brings passion and precision to every cut.",
        "email": "francis@barbershop.com",
        "phone": "(555) 123-4567",
        "social": {
            "instagram": "https://instagram.com",
            "facebook": "https://facebook.com"
        },
        "booking_policy": "Walk-ins welcome. Online booking available Mon-Sat 9AM-6PM.",
        "image": "francis.svg",
        "cover": "cover-francis.svg"
    },
    {
        "id": 2,
        "name": "Juan",
        "role": "Barber & Stylist",
        "bio": "Expert in modern cuts, styling, and beard care. Juan stays updated with the latest trends while maintaining classic technique.",
        "email": "juan@barbershop.com",
        "phone": "(555) 123-4568",
        "social": {
            "instagram": "https://instagram.com",
            "tiktok": "https://tiktok.com"
        },
        "booking_policy": "Online booking preferred. Available Tue-Sun 10AM-7PM.",
        "image": "juan.svg",
        "cover": "cover-juan.svg"
    }
]


SAMPLE_REVIEWS = [
    {
        "name": "Miguel Santos",
        "rating": 5,
        "comment": "Francis gave me one of the cleanest fades I have ever had. The haircut looked sharp, the lines were even, and the whole experience felt professional from start to finish.",
        "barber_id": 1,
        "created_at": "Sample review"
    },
    {
        "name": "Andre Cruz",
        "rating": 5,
        "comment": "I came in before an event and left feeling confident. The barber listened to what I wanted, explained what would suit my hair, and delivered a fresh cut.",
        "barber_id": 1,
        "created_at": "Sample review"
    },
    {
        "name": "Paolo Reyes",
        "rating": 5,
        "comment": "The shop feels clean, calm, and reliable. My haircut was detailed, my beard line-up was crisp, and I did not feel rushed at all.",
        "barber_id": 1,
        "created_at": "Sample review"
    },
    {
        "name": "Luis Mendoza",
        "rating": 5,
        "comment": "Juan did an amazing job with my haircut. He matched the style I showed him and made it look natural for my face shape.",
        "barber_id": 2,
        "created_at": "Sample review"
    },
    {
        "name": "Carlo Dela Cruz",
        "rating": 4,
        "comment": "Great service and friendly staff. The cut was clean, the appointment was easy, and I would recommend this barbershop to anyone looking for a reliable barber.",
        "barber_id": 2,
        "created_at": "Sample review"
    }
]


def review_stats(reviews):
    if not reviews:
        return {"average": "0.0", "count": 0, "five_star": 0}
    count = len(reviews)
    total = sum(int(review["rating"]) for review in reviews)
    five_star = sum(1 for review in reviews if int(review["rating"]) == 5)
    return {
        "average": f"{total / count:.1f}",
        "count": count,
        "five_star": five_star
    }


def build_availability_calendar(year, month, slots_by_date):
    month_days = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    weeks = []
    for week in month_days:
        weeks.append([
            {
                "date": str(day) if day else "",
                "slots": slots_by_date.get(day, [])
            }
            for day in week
        ])
    return {
        "month": f"{calendar.month_name[month]} {year}",
        "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "weeks": weeks
    }


def sample_slots_for_month(month):
    first_day = 4 + ((month - 1) % 3)
    second_day = 11 + ((month * 2) % 5)
    third_day = 18 + (month % 6)
    fourth_day = 24 + (month % 4)
    return {
        first_day: [
            {"time": "9:00 AM", "status": "available"},
            {"time": "10:30 AM", "status": "occupied"}
        ],
        second_day: [
            {"time": "1:00 PM", "status": "available"},
            {"time": "3:30 PM", "status": "available"}
        ],
        third_day: [
            {"time": "11:00 AM", "status": "occupied"},
            {"time": "4:00 PM", "status": "available"}
        ],
        fourth_day: [
            {"time": "9:30 AM", "status": "available"},
            {"time": "2:00 PM", "status": "occupied"}
        ],
    }


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    with db:
        db.execute('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            datetime TEXT NOT NULL,
            notes TEXT
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            barber_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # ensure older DBs get a barber_id column if missing
        try:
            cur = db.execute("PRAGMA table_info(reviews)")
            cols = [row[1] for row in cur.fetchall()]
            if 'barber_id' not in cols:
                db.execute('ALTER TABLE reviews ADD COLUMN barber_id INTEGER')
        except Exception:
            pass
    db.close()


init_db()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    services = [
        {
            "id": "haircut",
            "name": "Tailored Haircut",
            "duration": "30 min",
            "price": "$25",
            "description": "Classic fade, undercut, or textured cut tailored to your style and hair type."
        },
        {
            "id": "beard",
            "name": "Beard Trim & Shape",
            "duration": "15 min",
            "price": "$15",
            "description": "Professional beard grooming, shaping, and line-up for a polished look."
        },
        {
            "id": "combo",
            "name": "Cut + Beard Package",
            "duration": "45 min",
            "price": "$35",
            "description": "Complete grooming package: haircut and full beard service combined."
        },
        {
            "id": "wedding",
            "name": "Wedding Package",
            "duration": "60 min",
            "price": "$60",
            "description": "Premium grooming for your big day. Includes haircut, beard trim, and detailed line-up. Booking required 1 week prior."
        },
        {
            "id": "lineup",
            "name": "Beard Line-up",
            "duration": "10 min",
            "price": "$10",
            "description": "Quick touch-up for clean, sharp lines on cheeks, neck, and jaw."
        },
        {
            "id": "shave",
            "name": "Traditional Shave",
            "duration": "20 min",
            "price": "$20",
            "description": "Hot lather shave with straight razor for a smooth, luxurious finish."
        }
    ]
    booking_services = [
        ("haircut", "Haircut"),
        ("beard", "Beard Trim"),
        ("combo", "Cut + Beard"),
    ]
    availability_calendars = [
        build_availability_calendar(2026, month, sample_slots_for_month(month))
        for month in range(1, 13)
    ]
    about_info = {
        "title": "About Our Barbershop",
        "description": "Established in 2010, we've been serving our community with professional grooming and exceptional service.",
        "mission": "To provide the highest quality barbering services with attention to detail and genuine hospitality.",
        "hours": [
            ("Monday-Friday", "9:00 AM - 6:00 PM"),
            ("Saturday", "9:00 AM - 5:00 PM"),
            ("Sunday", "Closed")
        ],
        "values": [
            "Quality - We never compromise on excellence",
            "Professionalism - Expert service every time",
            "Community - Building relationships, one cut at a time",
            "Innovation - Blending tradition with modern styles"
        ]
    }
    location = {
        "name": "Classic Cuts Barbershop",
        "street": "123 Main Street",
        "city": "Your City",
        "state": "ST",
        "zip": "12345",
        "phone": "(555) 123-4567",
        "email": "info@barbershop.com",
        "latitude": "40.7128",
        "longitude": "-74.0060",
    }
    # feature the first team member as the face of the site
    featured = TEAM_MEMBERS[0]
    db = get_db()
    cur = db.execute('SELECT * FROM reviews WHERE barber_id = ? ORDER BY created_at DESC LIMIT 3', (featured['id'],))
    featured_reviews = [dict(row) for row in cur.fetchall()]
    if not featured_reviews:
        featured_reviews = [review for review in SAMPLE_REVIEWS if review["barber_id"] == featured["id"]][:3]
    cur = db.execute('SELECT * FROM reviews ORDER BY created_at DESC')
    all_reviews = [dict(row) for row in cur.fetchall()]
    if not all_reviews:
        all_reviews = SAMPLE_REVIEWS
    cur = db.execute('SELECT * FROM gallery ORDER BY created_at DESC')
    images = cur.fetchall()
    featured_stats = review_stats([review for review in all_reviews if review["barber_id"] == featured["id"]])
    overall_stats = review_stats(all_reviews)
    return render_template(
        'index.html',
        services=services,
        booking_services=booking_services,
        availability_calendars=availability_calendars,
        featured=featured,
        featured_reviews=featured_reviews,
        team=TEAM_MEMBERS,
        images=images,
        about=about_info,
        location=location,
        reviews=all_reviews,
        featured_stats=featured_stats,
        overall_stats=overall_stats,
    )


@app.route('/services')
def services():
    services_list = [
        ("haircut", "Tailored Haircut"),
        ("beard", "Beard Trim & Shape"),
        ("combo", "Cut + Beard Package"),
        ("wedding", "Wedding Package"),
        ("lineup", "Beard Line-up"),
        ("shave", "Traditional Shave"),
    ]
    return render_template('book.html', services=services_list)


@app.route('/book', methods=['GET', 'POST'])
def book():
    services_list = [
        ("haircut", "Haircut"),
        ("beard", "Beard Trim"),
        ("combo", "Cut + Beard"),
    ]
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        service = request.form.get('service', '')
        datetime = request.form.get('datetime', '').strip()
        notes = request.form.get('notes', '').strip()
        if not name or not phone or not service or not datetime:
            error = "Please fill the required fields."
            return render_template('book.html', services=services_list, error=error, form=request.form)
        db = get_db()
        db.execute('INSERT INTO appointments (name, phone, service, datetime, notes) VALUES (?, ?, ?, ?, ?)',
                   (name, phone, service, datetime, notes))
        db.commit()
        return render_template('booking_success.html', name=name)
    return render_template('book.html', services=services_list)


@app.route('/appointments')
def appointments():
    db = get_db()
    cur = db.execute('SELECT * FROM appointments ORDER BY datetime DESC')
    rows = cur.fetchall()
    return render_template('appointments.html', appointments=rows)


# Enhanced Services with Details
@app.route('/services')
def services_page():
    services_list = [
        {
            "id": "haircut",
            "name": "Tailored Haircut",
            "duration": "30 min",
            "price": "$25",
            "description": "Classic fade, undercut, or textured cut tailored to your style and hair type."
        },
        {
            "id": "beard",
            "name": "Beard Trim & Shape",
            "duration": "15 min",
            "price": "$15",
            "description": "Professional beard grooming, shaping, and line-up for a polished look."
        },
        {
            "id": "combo",
            "name": "Cut + Beard Package",
            "duration": "45 min",
            "price": "$35",
            "description": "Complete grooming package: haircut and full beard service combined."
        },
        {
            "id": "wedding",
            "name": "Wedding Package",
            "duration": "60 min",
            "price": "$60",
            "description": "Premium grooming for your big day. Includes haircut, beard trim, and detailed line-up. Booking required 1 week prior."
        },
        {
            "id": "lineup",
            "name": "Beard Line-up",
            "duration": "10 min",
            "price": "$10",
            "description": "Quick touch-up for clean, sharp lines on cheeks, neck, and jaw."
        },
        {
            "id": "shave",
            "name": "Traditional Shave",
            "duration": "20 min",
            "price": "$20",
            "description": "Hot lather shave with straight razor for a smooth, luxurious finish."
        }
    ]
    return render_template('services_detail.html', services=services_list)


# Team Page
@app.route('/team')
def team():
    return render_template('team.html', team=TEAM_MEMBERS)


# Individual Barber Profile Page
@app.route('/barber/<int:barber_id>')
def barber_profile(barber_id):
    barber = next((b for b in TEAM_MEMBERS if b['id'] == barber_id), None)
    if not barber:
        return "Barber not found", 404
    db = get_db()
    cur = db.execute('SELECT * FROM reviews WHERE barber_id = ? ORDER BY created_at DESC', (barber_id,))
    barber_reviews = [dict(row) for row in cur.fetchall()]
    if not barber_reviews:
        barber_reviews = [review for review in SAMPLE_REVIEWS if review["barber_id"] == barber_id]
    barber_stats = review_stats(barber_reviews)
    return render_template('barber_profile.html', barber=barber, barber_reviews=barber_reviews, barber_stats=barber_stats)


# Gallery Page
@app.route('/gallery')
def gallery():
    db = get_db()
    cur = db.execute('SELECT * FROM gallery ORDER BY created_at DESC')
    images = cur.fetchall()
    return render_template('gallery.html', images=images)


# About Page
@app.route('/about')
def about():
    about_info = {
        "title": "About Our Barbershop",
        "description": "Established in 2010, we've been serving our community with professional grooming and exceptional service.",
        "mission": "To provide the highest quality barbering services with attention to detail and genuine hospitality.",
        "hours": [
            ("Monday-Friday", "9:00 AM - 6:00 PM"),
            ("Saturday", "9:00 AM - 5:00 PM"),
            ("Sunday", "Closed")
        ],
        "values": [
            "Quality - We never compromise on excellence",
            "Professionalism - Expert service every time",
            "Community - Building relationships, one cut at a time",
            "Innovation - Blending tradition with modern styles"
        ]
    }
    return render_template('about.html', about=about_info)


# Address/Location Page
@app.route('/address')
def address():
    location = {
        "name": "Classic Cuts Barbershop",
        "street": "123 Main Street",
        "city": "Your City",
        "state": "ST",
        "zip": "12345",
        "phone": "(555) 123-4567",
        "email": "info@barbershop.com",
        "latitude": "40.7128",
        "longitude": "-74.0060",
        "map_embed_url": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3024.1234567890!2d-74.0060!3d40.7128"
    }
    return render_template('address.html', location=location)


# Reviews Page
@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        rating = request.form.get('rating', 5, type=int)
        comment = request.form.get('comment', '').strip()
        barber_id = request.form.get('barber_id', 1, type=int)
        if name and comment:
            db = get_db()
            db.execute('INSERT INTO reviews (name, rating, comment, barber_id) VALUES (?, ?, ?, ?)',
                       (name, rating, comment, barber_id))
            db.commit()
            return render_template('review_success.html', name=name)
    db = get_db()
    cur = db.execute('SELECT * FROM reviews ORDER BY created_at DESC')
    all_reviews = [dict(row) for row in cur.fetchall()]
    if not all_reviews:
        all_reviews = SAMPLE_REVIEWS
    return render_template('reviews.html', reviews=all_reviews, team=TEAM_MEMBERS)


if __name__ == '__main__':
    app.run(debug=True)
