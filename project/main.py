from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file, jsonify
from flask_login import login_required, current_user
from flask_mail import Mail, Message
import os
from datetime import datetime, time as dt_time
from .__init__ import db
from .__init__ import create_app
from dotenv import load_dotenv
from .models import User, Feedback, Office, Room, Desk, Parking, Booking
from sqlalchemy import desc, func
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

load_dotenv()
env_suffix = os.getenv('ENVIRONMENT')

main = Blueprint('main', __name__)
app = create_app()
app.config['ENV_VAR'] = env_suffix
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'email@gmail.com'
# app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
application = app
zuerich_tz = pytz.timezone('Europe/Zurich')


def clear_past_bookings():
    with app.app_context():
        now = datetime.now()
        now_timestamp = int(now.timestamp())
        bookings = Booking.query.filter(Booking.end < now_timestamp).all()
        for booking in bookings:
            db.session.delete(booking)
        db.session.commit()
    return


# scheduler = BackgroundScheduler()
# scheduler.add_job(clear_past_bookings, 'cron', day='*/1')
# scheduler.start()
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
        # Convert the incoming time strings to UTC timestamps
        start_requested_utc = datetime.strptime(start_time, '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)
        end_requested_utc = datetime.strptime(end_time, '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)

        # Convert the UTC times to Zurich time
        start_requested_zurich = start_requested_utc.astimezone(zuerich_tz)
        end_requested_zurich = end_requested_utc.astimezone(zuerich_tz)

        # Convert the Zurich times back to timestamps for storage
        start_requested = int(start_requested_zurich.timestamp())
        end_requested = int(end_requested_zurich.timestamp())
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
            else:
                session['flash_messages'].append(('Booking overlaps with other.', 'error'))
                flash_messages()
            db.session.commit()
    office_name = request.args.get('name')
    office_id = Office.query.filter_by(name=office_name).first().id
    rooms = Room.query.filter_by(office_id=office_id).order_by(Room.id.asc()).all()
    parking_spots = Parking.query.filter_by(office_id=office_id).order_by(Parking.name.asc()).all()
    bookings = Booking.query.all()
    return render_template('office.html', rooms=rooms, parking_spots=parking_spots, bookings=bookings)


@app.route('/room', methods=['GET', 'POST'])
@login_required
def room():
    if request.method == 'POST':
        desk_id = request.form.get('desk_id')
        start_time = request.form.get('start')
        end_time = request.form.get('end')

        start_requested = int(datetime.strptime(start_time, '%Y-%m-%dT%H:%M').timestamp())
        end_requested = int(datetime.strptime(end_time, '%Y-%m-%dT%H:%M').timestamp())
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
                session['flash_messages'].append(('Booking Successful', 'success'))
                flash_messages()
            else:
                session['flash_messages'].append(('Booking overlaps with other.', 'error'))
                flash_messages()
            db.session.commit()
    room_id = request.args.get('room_id')

    room = Room.query.filter_by(id=room_id).first()
    desks = Desk.query.filter_by(room_id=room_id).all()
    timezone = request.cookies.get('timezone', 'Europe/Zurich')
    bookings = Booking.query.all()
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
            found_desk = False
            found_parking = False
            bookings = Booking.query.all()
            for booking in bookings:
                if booking.desk_id == desk_id:
                    found_desk = True
                    break
                if booking.parking_id == parking_id:
                    found_parking = True
                    break
            if not found_desk and desk_id:
                desk = Desk.query.filter_by(id=desk_id).first()
                desk.reserved = False
                # desk.reserved_by = None
                # desk.user_id = None
            if not found_parking and parking_id:
                parking = Parking.query.filter_by(id=parking_id).first()
                parking.reserved = False
                # parking.reserved_by = None
                # parking.user_id = None
            db.session.commit()
    rooms = Room.query.all()
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
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
                sender='simplesolar.ie@gmail.com',
                recipients=['simplesolar.ie@gmail.com']
            )
            msg.body = f"Company name: {name}\nEmail address: {email_address}\nFeedback: {feedback_text}"
            mail.send(msg)
            return redirect(url_for('feedback'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('feedback'))
    return render_template('feedback.html')


def flash_messages():
    messages = session.get('flash_messages', [])
    for message in messages:
        flash(message[0], message[1])
    session['flash_messages'] = []


'''
waitress-serve --listen=*:8000 project.main:application
'''
