import sqlalchemy as sa
from datetime import datetime
from flask_migrate import Migrate
from flask_migrate import MigrateCommand
from flask_user import UserMixin
from sqlalchemy import Column, Integer, String
# from sqlalchemy_continuum import make_versioned

from IoCEngine import db

# from theIoC import manager

# make_versioned(user_cls=None)


class CtgryCode(db.Model):
    # __bind_key__ = 'IoC'
    # __versioned__ = {}
    __tablename__ = 'sb2file_ctgry_codes'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    code_name = db.Column(db.String(8), index=True, unique=True)
    header_code = db.Column(db.String(8), index=True)
    file_type_code = db.Column(db.String(8), index=True)

    def __repr__(self):
        return '<SB2 File Ctgry Code {}>'.format(self.code_name)


class DataProvider(db.Model):
    # __bind_key__ = 'IoC'
    # __versioned__ = {}
    __tablename__ = 'data_providers'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    code_name = db.Column(db.String(16), index=True, unique=True)
    dpid = db.Column(db.String(10), index=True, unique=True)
    sbmxn_pt = db.Column(db.String(5), index=True)
    ctgry = db.Column(db.String(5), index=True)
    typ = db.Column(db.String(5), index=True)
    day_first = db.Column(db.Boolean)

    def __repr__(self):
        return '<Data Provider {} ID: {}>'.format(self.code_name, self.dpid)
