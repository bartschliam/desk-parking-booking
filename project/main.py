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
from .models import User, Feedback
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
    return render_template('index.html')


@app.route('/company_details', methods=['GET', 'POST'])
@login_required
def company_details():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        company_address = request.form.get('company_address')

        existing_company = User.query.filter_by(company_name=company_name).first()
        existing_address = User.query.filter_by(company_address=company_address).first()
        if existing_company and existing_address and existing_company.id == existing_address.id and existing_company.id != current_user.id:
            session['flash_messages'].append(('That company name and address already exist.', 'danger'))
        else:
            company_representative = request.form.get('company_representative')
            company_mobile = request.form.get('company_mobile')
            company_landline = request.form.get('company_landline')
            company_email = request.form.get('company_email')
            company_identification_number = request.form.get('company_identification_number')
            company_method_of_yield = request.form.get('company_method_of_yield')

            current_user.company_name = company_name if company_name else ''
            current_user.company_representative = company_representative if company_representative else ''
            current_user.company_address = company_address if company_address else ''
            current_user.company_mobile = company_mobile if company_mobile else ''
            current_user.company_landline = company_landline if company_landline else ''
            current_user.company_email = company_email if company_email else ''
            current_user.company_identification_number = company_identification_number if company_identification_number else ''
            current_user.company_method_of_yield = company_method_of_yield if company_method_of_yield else ''
            db.session.commit()
            session['flash_messages'].append(('Details Updated', 'success'))
        flash_messages()
        return redirect(url_for('index'))
    return render_template('company_details.html', user=current_user)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        email_address = request.form.get('email_address')
        feedback_text = request.form.get('feedback')

        if company_name and email_address and feedback_text:  # Check if all fields are filled
            max_feedback_id = Feedback.query.order_by(desc(Feedback.id)).first()
            new_feedback = Feedback(
                id=max_feedback_id.id + 1 if max_feedback_id else 1,
                company_name=company_name,
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
            msg.body = f"Company name: {company_name}\nEmail address: {email_address}\nFeedback: {feedback_text}"
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
