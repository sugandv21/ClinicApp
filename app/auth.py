from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from . import db
from .models import User

auth_bp = Blueprint('auth', __name__, url_prefix='')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@auth_bp.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('auth.register_patient'))
        u = User(full_name=name, email=email, is_doctor=False)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Patient registered. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register_patient.html')

@auth_bp.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    if request.method == 'POST':
        name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('auth.register_doctor'))
        u = User(full_name=name, email=email, is_doctor=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Doctor account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register_doctor.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))
