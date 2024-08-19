from flask_login import UserMixin
from .__init__ import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    admin = db.Column(db.Boolean)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(1000))
    email_address = db.Column(db.String(1000))
    feedback = db.Column(db.String(10000))


class Office(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    office_id = db.Column(db.Integer, db.ForeignKey('office.id'))
    rows = db.Column(db.Integer)
    columns = db.Column(db.Integer)


class Desk(db.Model):
    __tablename__ = 'desk'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    reserved = db.Column(db.Boolean)
    reserved_by = db.Column(db.String(1000))
    reserved_until_date = db.Column(db.Date)
    reserved_until_time = db.Column(db.String(4))
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)

    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))


class Parking(db.Model):
    __tablename__ = 'parking'
    id = db.Column(db.Integer, primary_key=True)
    reserved = db.Column(db.Boolean)
    reserved_by = db.Column(db.String(1000))
    reserved_until_date = db.Column(db.Date)
    reserved_until_time = db.Column(db.String(4))

    office_id = db.Column(db.Integer, db.ForeignKey('office.id'))


'''
from project import db, create_app, models
db.create_all(app=create_app())
'''
