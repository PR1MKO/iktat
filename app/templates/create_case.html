from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, Case  # <-- import Case here

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('auth.register'))
        # Create new user
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('auth.dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@auth_bp.route('/cases/new', methods=['GET', 'POST'])
@login_required
def create_case():
    if request.method == 'POST':
        case_number = request.form['case_number']
        year = request.form['year']
        status = request.form['status']
        assigned_office = request.form['assigned_office']
        assigned_signatory = request.form['assigned_signatory']
        assigned_pathologist = request.form['assigned_pathologist']
        notes = request.form['notes']

        # Prevent duplicate case numbers
        if db.session.query(db.exists().where(Case.case_number == case_number)).scalar():
            flash('Case number already exists.')
            return redirect(url_for('auth.create_case'))

        case = Case(
            case_number=case_number,
            year=year,
            status=status,
            assigned_office=assigned_office,
            assigned_signatory=assigned_signatory,
            assigned_pathologist=assigned_pathologist,
            notes=notes
        )
        db.session.add(case)
        db.session.commit()
        flash('New case created successfully!')
        return redirect(url_for('auth.dashboard'))
    return render_template('create_case.html')
