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
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)

    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    room = db.relationship('Room', backref='desks')
    office_id = db.Column(db.Integer, db.ForeignKey('office.id'))
    office = db.relationship('Office', backref='desks')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='desks')


class Parking(db.Model):
    __tablename__ = 'parking'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    reserved = db.Column(db.Boolean)
    reserved_by = db.Column(db.String(1000))
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)

    office_id = db.Column(db.Integer, db.ForeignKey('office.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


'''
from project import db, create_app, models
db.create_all(app=create_app())
'''
