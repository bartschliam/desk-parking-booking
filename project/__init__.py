from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os


db = SQLAlchemy(engine_options={"pool_pre_ping": True})
load_dotenv()
database_uri = os.getenv('DATABASE_URI')


def create_app():
    app = Flask(__name__)
    no_wifi = os.getenv('NO_WIFI')
    if no_wifi != 'true':
        app.config.update(
            SQLALCHEMY_DATABASE_URI=database_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False
        )
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['SECRET_KEY'] = 'secret-key-goes-here'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
'''
Export to csv
psql "Connection string?options=endpoint%3Dep-long-hill-a2gyc3s6&sslmode=require"
COPY public.user TO stdout DELIMITER ',' CSV HEADER;

Import from csv
psql "Connection string?options=endpoint%3Dep-long-hill-a2gyc3s6&sslmode=require"
___copy public.user FROM 'C:/path/filename.csv' DELIMITER ',' CSV HEADER

psql "postgresql://bartschliam:LRwbVHKIX6T9@ep-long-hill-a2gyc3s6.eu-central-1.aws.neon.tech/solar_db?options=endpoint%3Dep-long-hill-a2gyc3s6&sslmode=require"
___copy public.panel FROM 'C:___Users___Liam Bartsch___Desktop___Relevant___Projects___solar___project___database___panel.csv' DELIMITER ',' CSV HEADER

'''