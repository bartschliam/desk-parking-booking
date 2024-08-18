from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file, jsonify
from flask_login import login_required, current_user
from flask_mail import Mail, Message
import requests
import os
import json
from datetime import datetime, date, timedelta
from .__init__ import db
from .__init__ import create_app
import stripe
from dotenv import load_dotenv
from .models import User, Feedback, Office, Room, Desk
import re
from sqlalchemy import desc, func

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
    office_name = request.args.get('name')
    office_id = Office.query.filter_by(name=office_name).first().id
    rooms = Room.query.filter_by(office_id=office_id).order_by(Room.id.asc()).all()
    return render_template('office.html', rooms=rooms)


@app.route('/room', methods=['GET', 'POST'])
@login_required
def room():
    room_id = request.args.get('room_id')
    room = Room.query.filter_by(id=room_id).first()
    desks = Desk.query.filter_by(room_id=room_id).all()

    return render_template('room.html', desks=desks, room=room)


@app.route('/book_desk', methods=['GET', 'POST'])
@login_required
def book_desk():
    return render_template('book_desk.html')


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
