from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file, jsonify, render_template_string
from flask_login import login_required, current_user
from flask_mail import Mail, Message
import os
from datetime import datetime, time as dt_time
from .__init__ import db
from .__init__ import create_app, flash_messages
from dotenv import load_dotenv
from .models import User, Feedback, Office, Room, Desk, Parking, Booking
from sqlalchemy import desc, func
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
import pytz
from itsdangerous.serializer import Serializer
from itsdangerous.url_safe import URLSafeSerializer
from itsdangerous import BadSignature
from passlib.hash import sha256_crypt
from markupsafe import Markup


load_dotenv()
env_suffix = os.getenv('ENVIRONMENT')

main = Blueprint('main', __name__)
app = create_app()
app.config['ENV_VAR'] = env_suffix
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
application = app
zurich_tz = timezone('Europe/Zurich')
utc_tz = timezone('UTC')

reset_password_email_html_content = """
<p>Hello,</p>
<p>You are receiving this email because you requested a password reset for your account.</p>
<p>
    To reset your password
    <a href="{{ reset_password_url }}">click here</a>.
</p>
<p>
    Alternatively, you can paste the following link in your browser's address bar: <br>
    {{ reset_password_url }}
</p>
<p>If you have not requested a password reset please contact someone from the development team.</p>
<p>
    Thank you!
</p>
"""


def update_desks_parkings(desk_id, parking_id):
    found_desk = False
    found_parking = False
    bookings = Booking.query.all()
    for booking in bookings:
        if booking.desk_id is not None and booking.desk_id == desk_id:
            found_desk = True
            break
        if booking.parking_id is not None and booking.parking_id == parking_id:
            found_parking = True
            break
    if not found_desk and desk_id:
        desk = Desk.query.filter_by(id=desk_id).first()
        desk.reserved = False
    if not found_parking and parking_id:
        parking = Parking.query.filter_by(id=parking_id).first()
        parking.reserved = False
    db.session.commit()
    return


def clear_past_bookings():
    with app.app_context():
        now = datetime.now()
        now_timestamp = int(now.timestamp())
        zurich_tz = pytz.timezone('Europe/Zurich')
        now_zurich = datetime.now(zurich_tz)
        now_timestamp = int(now_zurich.timestamp())
        expired_bookings = Booking.query.filter(Booking.end < now_timestamp).all()
        for expired_booking in expired_bookings:
            desk_id = expired_booking.desk_id
            parking_id = expired_booking.parking_id
            db.session.delete(expired_booking)
            db.session.commit()
            update_desks_parkings(desk_id, parking_id)
    return


scheduler = BackgroundScheduler()
scheduler.add_job(clear_past_bookings, 'cron', hour=3, minute=0)
scheduler.start()
# if __name__ == '__main__':
#     app = create_app()
#     app.run(host='0.0.0.0', debug=False)
#     # from waitress import serve
#     # serve(app, host='0.0.0.0', port=8080)


@app.route('/')
def index():
    session['flash_messages'] = []
    offices = Office.query.all()
    return render_template('index.html', offices=offices)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != current_user.id:
            session['flash_messages'].append(('That email already exist.', 'danger'))
        else:
            name = request.form.get('name')

            current_user.name = name if name else ''
            current_user.email = email if email else ''
            db.session.commit()
            session['flash_messages'].append(('Details Updated', 'success'))
        flash_messages()
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)


@app.route('/office', methods=['GET', 'POST'])
@login_required
def office():
    if request.method == 'POST':
        spot_id = request.form.get('spot_id')
        start_time = request.form.get('start')
        end_time = request.form.get('end')
        start_time_zurich = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time_zurich = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        start_time_utc = zurich_tz.localize(start_time_zurich).astimezone(utc_tz)
        end_time_utc = zurich_tz.localize(end_time_zurich).astimezone(utc_tz)
        start_requested = int(start_time_utc.timestamp())
        end_requested = int(end_time_utc.timestamp())
        parking = Parking.query.filter_by(id=spot_id).first()
        bookings = Booking.query.filter_by(parking_id=spot_id).all()
        if end_requested > start_requested:
            valid = True
            for booking in bookings:
                if not (end_requested <= booking.start or start_requested >= booking.end):
                    valid = False
                    break
            if valid:
                parking.reserved = True
                max_booking_id = Booking.query.order_by(desc(Booking.id)).first()
                booking = Booking(
                    id=max_booking_id.id + 1 if max_booking_id else 1,
                    user_id=current_user.id,
                    start=start_requested,
                    type='parking',
                    end=end_requested,
                    parking_id=spot_id,
                    reserved_by=current_user.name
                )
                db.session.add(booking)
                session['flash_messages'].append(('Booking Successful', 'success'))
                flash_messages()
                parking = Parking.query.filter_by(id=booking.parking_id).first()
                office = Office.query.filter_by(id=parking.office_id).first()
                msg = Message(
                    subject='Parking Booking Successful ✅',
                    sender=os.getenv('MAIL_EMAIL'),
                    recipients=[current_user.email]
                )
                start = datetime.fromtimestamp(booking.start, tz=pytz.UTC).astimezone(zurich_tz).strftime('%A %Y/%m/%d %H:%M %Z')
                end = datetime.fromtimestamp(booking.end, tz=pytz.UTC).astimezone(zurich_tz).strftime('%A %Y/%m/%d %H:%M %Z')
                msg.html = f"""
                    <html>
                        <body>
                            <h3>Booking Details</h3>
                            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                                <tr>
                                    <th align="left">Booking ID</th>
                                    <td>{booking.id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Author</th>
                                    <td>{booking.reserved_by}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Author ID</th>
                                    <td>{booking.user_id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Parking ID</th>
                                    <td>{booking.parking_id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Parking Name</th>
                                    <td>{parking.name}</td>
                                </tr>
                                <tr>
                                    <th align="left">Office Name</th>
                                    <td>{office.name}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Start</th>
                                    <td>{start}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking End</th>
                                    <td>{end}</td>
                                </tr>
                            </table>
                        </body>
                    </html>
                    """
                send_mail(msg)
            else:
                session['flash_messages'].append(('Booking overlaps with other.', 'error'))
                flash_messages()
            db.session.commit()
    office_name = request.args.get('name')
    office_id = Office.query.filter_by(name=office_name).first().id
    rooms = Room.query.filter_by(office_id=office_id).order_by(Room.id.asc()).all()
    parking_spots = Parking.query.filter_by(office_id=office_id).order_by(Parking.name.asc()).all()
    bookings = Booking.query.order_by(Booking.start.desc()).all()
    return render_template('office.html', rooms=rooms, parking_spots=parking_spots, bookings=bookings)


@app.route('/room', methods=['GET', 'POST'])
@login_required
def room():
    if request.method == 'POST':
        desk_id = request.form.get('desk_id')
        start_time = request.form.get('start')
        end_time = request.form.get('end')

        start_time_zurich = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time_zurich = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        start_time_utc = zurich_tz.localize(start_time_zurich).astimezone(utc_tz)
        end_time_utc = zurich_tz.localize(end_time_zurich).astimezone(utc_tz)
        start_requested = int(start_time_utc.timestamp())
        end_requested = int(end_time_utc.timestamp())
        permanent = 'permanent' in request.form
        desk = Desk.query.filter_by(id=desk_id).first()
        bookings = Booking.query.filter_by(desk_id=desk_id).all()
        if end_requested > start_requested:
            valid = True
            for booking in bookings:
                if not (end_requested <= booking.start or start_requested >= booking.end):
                    valid = False
                    break
            if valid:
                desk.reserved = True
                max_booking_id = Booking.query.order_by(desc(Booking.id)).first()
                booking = Booking(
                    id=max_booking_id.id + 1 if max_booking_id else 1,
                    user_id=current_user.id,
                    start=start_requested,
                    type='desk',
                    end=end_requested,
                    desk_id=desk_id,
                    reserved_by=current_user.name
                )
                db.session.add(booking)
                desk = Desk.query.filter_by(id=booking.desk_id).first()
                room = Room.query.filter_by(id=desk.room_id).first()
                office = Office.query.filter_by(id=room.office_id).first()
                session['flash_messages'].append(('Booking Successful', 'success'))
                flash_messages()
                msg = Message(
                    subject='Desk Booking Successful ✅',
                    sender=os.getenv('MAIL_EMAIL'),
                    recipients=[current_user.email]
                )
                start = datetime.fromtimestamp(booking.start, tz=pytz.UTC).astimezone(zurich_tz).strftime('%A %Y/%m/%d %H:%M %Z')
                end = datetime.fromtimestamp(booking.end, tz=pytz.UTC).astimezone(zurich_tz).strftime('%A %Y/%m/%d %H:%M %Z')
                msg.html = f"""
                    <html>
                        <body>
                            <h3>Booking Details</h3>
                            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                                <tr>
                                    <th align="left">Booking ID</th>
                                    <td>{booking.id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Author</th>
                                    <td>{booking.reserved_by}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Author ID</th>
                                    <td>{booking.user_id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Desk ID</th>
                                    <td>{booking.desk_id}</td>
                                </tr>
                                <tr>
                                    <th align="left">Desk Name</th>
                                    <td>{desk.name}</td>
                                </tr>
                                <tr>
                                    <th align="left">Room Name</th>
                                    <td>{room.name}</td>
                                </tr>
                                <tr>
                                    <th align="left">Office Name</th>
                                    <td>{office.name}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking Start</th>
                                    <td>{start}</td>
                                </tr>
                                <tr>
                                    <th align="left">Booking End</th>
                                    <td>{end}</td>
                                </tr>
                            </table>
                        </body>
                    </html>
                    """
                send_mail(msg)
            else:
                session['flash_messages'].append(('Booking overlaps with other.', 'error'))
                flash_messages()
            db.session.commit()
    room_id = request.args.get('room_id')
    room = Room.query.filter_by(id=room_id).first()
    desks = Desk.query.filter_by(room_id=room_id).all()
    timezone = request.cookies.get('timezone', 'Europe/Zurich')
    bookings = Booking.query.order_by(Booking.start.desc()).all()
    return render_template('room.html', desks=desks, room=room, timezone=timezone, bookings=bookings)


@app.route('/desks', methods=['GET', 'POST'])
@login_required
def desks():
    desks = Desk.query.filter_by(user_id=current_user.id).all()
    return render_template('desks.html', desks=desks)


@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        if booking_id:
            booking = Booking.query.filter_by(id=booking_id).first()
            desk_id = booking.desk_id
            parking_id = booking.parking_id
            db.session.delete(booking)
            db.session.commit()
            update_desks_parkings(desk_id, parking_id)
            db.session.commit()
    rooms = Room.query.all()
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.start.desc()).all()
    booking_desk_ids = [booking.desk_id for booking in bookings if booking.desk_id is not None]
    booking_parking_ids = [booking.parking_id for booking in bookings if booking.parking_id is not None]
    desks = Desk.query.filter(Desk.id.in_(booking_desk_ids)).all()
    parkings = Parking.query.filter(Parking.id.in_(booking_parking_ids)).all()
    return render_template('bookings.html', desks=desks, parkings=parkings, rooms=rooms, bookings=bookings)


@app.route('/book_parking', methods=['GET', 'POST'])
@login_required
def book_parking():
    return render_template('book_parking.html')


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name')
        email_address = request.form.get('email_address')
        feedback_text = request.form.get('feedback')

        if name and email_address and feedback_text:  # Check if all fields are filled
            max_feedback_id = Feedback.query.order_by(desc(Feedback.id)).first()
            new_feedback = Feedback(
                id=max_feedback_id.id + 1 if max_feedback_id else 1,
                name=name,
                email_address=email_address,
                feedback=feedback_text
            )
            db.session.add(new_feedback)
            db.session.commit()

            # Flash a success message
            flash('Feedback submitted successfully!', 'success')

            msg = Message(
                subject='New Feedback Form Submitted',
                sender=os.getenv('MAIL_EMAIL'),
                recipients=[os.getenv('MAIL_EMAIL')]
            )
            msg.body = f"Name: {name}\nEmail address: {email_address}\nFeedback: {feedback_text}"
            send_mail(msg)
            return redirect(url_for('feedback'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('feedback'))
    return render_template('feedback.html')


def send_mail(message):
    mail.send(message)
    return


def generate_reset_password_token(self):
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(self.email, salt=self.password)


def send_reset_password_email(user):
    reset_password_url = url_for('reset_password', token=generate_reset_password_token(user), user_id=user.id, _external=True)
    safe_reset_password_url = Markup(reset_password_url)

    msg = Message(
        subject='Reset your password',
        sender=os.getenv('MAIL_EMAIL'),
        recipients=[user.email]
    )
    msg.html = render_template_string(reset_password_email_html_content, reset_password_url=safe_reset_password_url)
    send_mail(msg)
    return


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            session['flash_messages'].append(('Email not found', 'error'))
            flash_messages()
            return redirect(url_for('reset_password_request'))
        send_reset_password_email(user)
        session['flash_messages'].append(('Instructions sent if the email exists', 'success'))
        flash_messages()
    return render_template('reset_password_request.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        token = request.args.get('token')
        user_id = request.args.get('user_id')
    else:
        token = request.form.get('token')
        user_id = request.form.get('user_id')
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        session['flash_messages'].append(("Did not find user", "error"))
        flash_messages()
        return render_template('login.html')
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    try:
        token_user_email = serializer.loads(
            token,
            salt=user.password
        )
    except BadSignature:
        session['flash_messages'].append(("Bad token", "error"))
        flash_messages()
        return render_template('login.html')
    if token_user_email != user.email:
        session['flash_messages'].append(("Email doesn't match", "error"))
        flash_messages()
        return render_template('login.html')
    if request.method == 'POST':
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if not password1 or not password2:
            session['flash_messages'].append(("Password can't be empty", "error"))
            flash_messages()
        if password1 != password2:
            session['flash_messages'].append(('Passwords do not match', 'error'))
            flash_messages()
        password = sha256_crypt.hash(password1)
        user.password = password
        db.session.commit()
        session['flash_messages'].append(('Password reset', 'success'))
        flash_messages()
        return render_template('index.html')
    return render_template('reset_password.html', token=token, user_id=user_id)


'''
waitress-serve --listen=*:8000 project.main:application
'''
