from flask import render_template

from . import investigations_bp


@investigations_bp.route('/')
def list_investigations():
    return render_template('investigations/index.html')


@investigations_bp.route('/new')
def new_investigation():
    return 'stub'