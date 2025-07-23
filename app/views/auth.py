import os
from datetime import datetime, timedelta, date
import pytz
from app.utils.time_utils import now_local
from collections import defaultdict
from flask import (
    Blueprint, render_template, redirect, url_for, request,
    flash, current_app, send_from_directory, jsonify, Response, abort
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from werkzeug.utils import secure_filename, safe_join
from sqlalchemy import or_, and_, func
from app.models import UploadedFile, User, Case, AuditLog, ChangeLog
from app.forms import CaseIdentifierForm
from app import csrf                    # CSRFProtect instance
from app import db                      # SQLAlchemy instance
from app.email_utils import send_email
from app.audit import log_action
from app.tasks import auto_close_stale_cases
from ..utils.case_helpers import build_case_context
from ..utils.roles import roles_required
from app.routes import handle_file_upload
import csv
import io
import codecs

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/cases/<int:case_id>/changelog.csv')
@login_required
@roles_required('admin')
def export_changelog_csv(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    entries = ChangeLog.query.filter_by(case_id=case.id).order_by(ChangeLog.timestamp).all()

    # Group entries by same editor within 5 minutes
    grouped = []
    current_group = []
    last_ts = None
    last_user = None
    time_window = timedelta(minutes=5)

    for e in entries:
        if last_user == e.edited_by and last_ts and (e.timestamp - last_ts) <= time_window:
            current_group.append(e)
        else:
            if current_group:
                grouped.append(current_group)
            current_group = [e]
        last_ts = e.timestamp
        last_user = e.edited_by
    if current_group:
        grouped.append(current_group)

    si = io.StringIO()
    writer = csv.writer(si, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Timestamp", "Edited By", "Fields Changed", "Old Values", "New Values"])

    for group in grouped:
        ts = group[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')
        user = group[0].edited_by
        fields = []
        old_vals = []
        new_vals = []
        for entry in group:
            fields.append(entry.field_name)
            old_vals.append(entry.old_value or "")
            new_vals.append(entry.new_value or "")
        writer.writerow([
            ts,
            user,
            ", ".join(fields),
            ", ".join(old_vals),
            ", ".join(new_vals)
        ])

    # Add BOM for Excel UTF-8 detection
    bom = codecs.BOM_UTF8.decode('utf-8')
    output = bom + si.getvalue()

    return Response(
        output,
        mimetype='text/csv; charset=utf-8',
        headers={
            "Content-Disposition": f"attachment; filename=changelog_{case.case_number}.csv"
        }
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            log_action("User logged in")
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
    # Auto-close stale cases
    num_closed = auto_close_stale_cases()
    if num_closed:
        flash(f"{num_closed} case(s) auto-closed as 'lejárt'.", "info")

    now = datetime.now(pytz.UTC)
    today_start = datetime(now.year, now.month, now.day, tzinfo=pytz.UTC)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = datetime(now.year, now.month, 1, tzinfo=pytz.UTC)

    total_open    = Case.query.filter(Case.status != 'lezárva').count()
    new_today     = Case.query.filter(Case.registration_time >= today_start).count()
    new_this_week = Case.query.filter(Case.registration_time >= week_start).count()
    new_this_month = Case.query.filter(Case.registration_time >= month_start).count()
    closed_cases = Case.query.filter(Case.status.in_(['lezárt', 'lejárt'])).count()
    overdue_count = Case.query.filter(Case.status == 'lejárt').count()
    status_counts = dict(db.session.query(Case.status, func.count()).group_by(Case.status).all())
    status_counts_list = list(status_counts.items())
    missing_fields = Case.query.filter(
        (Case.expert_1 == None) | (Case.expert_1 == '') |
        (Case.describer == None) | (Case.describer == '')
    ).filter(Case.status != 'lezárva').all()
    upcoming_deadlines = Case.query.filter(
        Case.deadline >= now,
        Case.deadline <= now + timedelta(days=14),
        Case.status != 'lezárva'
    ).all()
    overdue_cases = Case.query.filter_by(status='lejárt').all()

    template_ctx = dict(
        status_counts_list=status_counts_list,
        user=current_user,
        total_open=total_open,
        new_today=new_today,
        new_this_week=new_this_week,
        new_this_month=new_this_month,
        closed_cases=closed_cases,
        overdue_count=overdue_count,
        status_counts=status_counts,
        missing_fields=missing_fields,
        upcoming_deadlines=upcoming_deadlines,
        overdue_cases=overdue_cases,
    )

    if current_user.role == 'admin':
        template_ctx.update({
            "recent_logins": AuditLog.query.filter_by(action='User logged in')
                .order_by(AuditLog.timestamp.desc()).limit(5).all(),
            "most_active_users": db.session.query(
                ChangeLog.edited_by, func.count(ChangeLog.id)
            )
            .group_by(ChangeLog.edited_by)
            .order_by(func.count(ChangeLog.id).desc())
            .limit(5)
            .all()
        })
        return render_template("dashboards/dashboard_admin.html", **template_ctx)

    dashboards = {
        'iroda':    "dashboards/dashboard_iroda.html",
        'szignáló': "dashboards/dashboard_szignalo.html",
        'szakértő': "dashboards/dashboard_szakerto.html",
        'leíró':    "dashboards/dashboard_leiro.html",
    }
    tpl = dashboards.get(current_user.role)
    if tpl:
        return render_template(tpl, **template_ctx)

    flash("Ismeretlen szerepkör. Kérjük, forduljon az adminisztrátorhoz.")
    return redirect(url_for('auth.logout'))

@auth_bp.route('/cases')
@login_required
def list_cases():
    sort_by = request.args.get('sort_by', 'case_number')
    sort_order = request.args.get('sort_order', 'desc')

    status_filter = request.args.get('status', '')
    case_type_filter = request.args.get('case_type', '')
    search_query = request.args.get('search', '').strip()

    query = Case.query
    filters = []

    if status_filter:
        filters.append(Case.status == status_filter)
    if case_type_filter:
        filters.append(Case.case_type == case_type_filter)
    if search_query:
        pat = f"%{search_query}%"
        filters.append(or_(
            Case.case_number.ilike(pat),
            Case.deceased_name.ilike(pat),
            Case.case_type.ilike(pat),
            Case.status.ilike(pat),
            Case.institution_name.ilike(pat),
            Case.external_case_number.ilike(pat),
            Case.expert_1.ilike(pat),
            Case.expert_2.ilike(pat),
            Case.describer.ilike(pat),
        ))
    if filters:
        query = query.filter(and_(*filters))

    # Determine order_by column and direction
    order_col = Case.case_number if sort_by == 'case_number' else Case.deadline
    if sort_order == 'desc':
        order_col = order_col.desc()
    else:
        order_col = order_col.asc()

    now = datetime.now(pytz.UTC)
    expired_cases = (
        query.filter(Case.deadline < now)
             .order_by(order_col)
             .all()
    )
    active_cases = (
        query.filter(or_(Case.deadline >= now, Case.deadline == None))
             .order_by(order_col)
             .all()
    )
    cases = expired_cases + active_cases

    users = User.query.all()
    users_map = {u.username: u for u in users}

    query_params = request.args.to_dict()

    return render_template(
        'list_cases.html',
        cases=cases,
        users_map=users_map,
        sort_by=sort_by,
        sort_order=sort_order,
        query_params=query_params,
        status_filter=status_filter,
        case_type_filter=case_type_filter,
        search_query=search_query,
        today=now.date()
    )

@auth_bp.route('/cases/<int:case_id>')
@login_required
def case_detail(case_id):
    case = db.session.get(Case, case_id) or abort(404)

    ctx = build_case_context(case)
    ctx['changelog_entries'] = [
        e for e in ctx['changelog_entries'] if e.field_name != 'notes'
    ]

    return render_template(
        'case_detail.html',
        case=case,
        **ctx
    )

@auth_bp.route('/cases/closed')
@login_required
def closed_cases():
    closed = Case.query.filter(Case.status.in_(['lejárt','lezárva']))\
             .order_by(Case.deadline.desc()).all()
    return render_template('closed_cases.html', cases=closed)

@auth_bp.route('/cases/new', methods=['GET','POST'])
@login_required
@roles_required('admin', 'iroda')
def create_case():
    class DummyCase:
        notes = ''
        case_type = ''
        szakerto = ''
        expert_2 = ''
        describer = ''
        # Add more default fields as needed

    form = CaseIdentifierForm(request.form if request.method == 'POST' else None)

    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()
    leiro_users    = User.query.filter_by(role='leíró').order_by(User.username).all()
    szakerto_choices = [('', '(opcionális)')] + [
        (u.username, u.screen_name or u.username) for u in szakerto_users
    ]
    leiro_choices = [('', '(opcionális)')] + [
        (u.username, u.screen_name or u.username) for u in leiro_users
    ]
    case = DummyCase()  # Always available for the template/macros

    if request.method == 'POST':
        missing = []
        if not request.form.get('case_type'):
            missing.append('Típus')
        if not request.form.get('registration_time'):
            missing.append('Regisztrálva')
        if not request.form.get('beerk_modja'):
            missing.append('Beérkezés módja')
        if missing:
            flash(', '.join(missing) + ' kitöltése kötelező.')
        if not form.validate():
            for err in form.external_id.errors:
                flash(err)
        if missing or form.errors:
            return render_template(
                'create_case.html',
                szakerto_users=szakerto_users,
                leiro_users=leiro_users,
                szakerto_choices=szakerto_choices,
                leiro_choices=leiro_choices,
                case=case,
                form=form
            )
        birth_date = None
        if request.form.get('birth_date'):
            birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
        reg_time_str = request.form.get('registration_time')
        if reg_time_str:
            registration_time = datetime.strptime(reg_time_str, '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.UTC)
        else:
            registration_time = datetime.now(pytz.UTC)
        year = registration_time.year
        count = Case.query.filter(
            func.strftime("%Y", Case.registration_time) == str(year)
        ).count() + 1
        case_number = f"{year}-{count:03d}"
        notes = request.form.get('notes', '').strip() or None

        # --- Handle the new "További adatok" fields ---
        beerk_modja  = request.form.get('beerk_modja', '').strip() or None
        poszeidon    = request.form.get('poszeidon', '').strip() or None
        lanykori_nev = request.form.get('lanykori_nev', '').strip() or None
        szul_hely    = request.form.get('szul_hely', '').strip() or None
        taj_szam     = request.form.get('taj_szam', '').strip() or None

        new_case = Case(
            case_number=case_number,
            case_type=request.form['case_type'],
            deceased_name=request.form.get('deceased_name'),
            institution_name=request.form.get('institution_name'),
            external_case_number=form.external_id.data,
            temp_id=form.temp_id.data,
            birth_date=birth_date,
            registration_time=registration_time,
            status='beérkezett',
            expert_1=request.form.get('expert_1'),
            expert_2=request.form.get('expert_2'),
            describer=request.form.get('describer'),
            notes=notes,

            # Save new fields
            beerk_modja=beerk_modja,
            poszeidon=poszeidon,
            lanykori_nev=lanykori_nev,
            szul_hely=szul_hely,
            taj_szam=taj_szam,
        )
        new_case.deadline = registration_time + timedelta(days=30)
        db.session.add(new_case)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return render_template(
                'create_case.html',
                szakerto_users=szakerto_users,
                leiro_users=leiro_users,
                szakerto_choices=szakerto_choices,
                leiro_choices=leiro_choices,
                case=case,
                form=form
            )
        flash('New case created.', 'success')
        return redirect(url_for('auth.case_detail', case_id=new_case.id))

    return render_template(
        'create_case.html',
        szakerto_users=szakerto_users,
        leiro_users=leiro_users,
        szakerto_choices=szakerto_choices,
        leiro_choices=leiro_choices,
        case=case,
        form=form  # ✅ FIXED HERE
    )

@auth_bp.route('/cases/<int:case_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'iroda')
def edit_case(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()
    leiro_users    = User.query.filter_by(role='leíró').order_by(User.username).all()
    if request.method == 'POST':
        # ... existing field handling ...
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return render_template('edit_case.html', case=case, szakerto_users=szakerto_users, leiro_users=leiro_users)
        flash('Az ügy módosításai elmentve.', 'success')
        return redirect(url_for('auth.case_detail', case_id=case.id))
    return render_template(
        'edit_case.html',
        case=case,
        szakerto_users=szakerto_users,
        leiro_users=leiro_users
    )

@auth_bp.route('/cases/<int:case_id>/upload', methods=['POST'])
@login_required
@roles_required('admin', 'iroda', 'szakértő', 'leíró')
def upload_file(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if case.status == 'lezárva':
        flash('Case is finalized. Uploads are disabled.', 'danger')
        return redirect(url_for('auth.case_detail', case_id=case_id))
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(case_id))
    os.makedirs(upload_folder, exist_ok=True)
    files = request.files.getlist('file')
    if not files:
        flash('No files selected', 'warning')
        return redirect(request.referrer or url_for('auth.case_detail', case_id=case_id))
    saved = []
    for f in files:
        fn = secure_filename(f.filename)
        if fn:
            try:
                f.save(os.path.join(upload_folder, fn))
            except Exception as e:
                current_app.logger.error(f"File save failed: {e}")
                flash("A fájl mentése nem sikerült.", "danger")
                continue
            upload_rec = UploadedFile(
                case_id   = case.id,
                filename  = fn,
                uploader  = current_user.username,
                upload_time = datetime.now(pytz.UTC)
            )
            db.session.add(upload_rec)
            saved.append(fn)
            log_action("File uploaded", f"{fn} for case {case.case_number}")
    if saved:
        case.uploaded_files = ','.join(filter(None, (case.uploaded_files or '').split(',') + saved))
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return redirect(request.referrer or url_for('auth.case_detail', case_id=case_id))
    flash(f'Uploaded: {", ".join(saved)}', 'success')
    if request.referrer and '/ugyeim/' in request.referrer:
        return redirect(url_for('main.elvegzem', case_id=case_id))
    else:
        return redirect(url_for('auth.case_detail', case_id=case_id))

@auth_bp.route('/cases/<int:case_id>/files/<path:filename>')
@login_required
@roles_required('admin', 'iroda', 'szakértő', 'leíró')
def download_file(case_id, filename):
    base_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(case_id))
    
    try:
        full_path = safe_join(base_dir, filename)
        if full_path is None:
            raise ValueError("unsafe path")
    except Exception:
        current_app.logger.warning(
            f"Path traversal attempt for case {case_id}: {filename}"
        )
        abort(403)

    if not os.path.isfile(full_path):
        current_app.logger.warning(
            f"File not found for case {case_id}: {full_path}"
        )
        abort(404)
        
    current_app.logger.info(f"Sending file: {full_path}")
    log_action("File downloaded", f"{filename} from case {case_id}")
    return send_from_directory(base_dir, filename, as_attachment=True)


@auth_bp.route('/szignal_cases')
@login_required
@roles_required('szignáló')
def szignal_cases():

    # Cases where both experts are missing (szignálandó)
    szignalando_cases = Case.query.filter(
        and_(
            or_(Case.expert_1 == None, Case.expert_1 == ''),
            or_(Case.expert_2 == None, Case.expert_2 == '')
        )
    ).order_by(Case.registration_time.desc()).all()

    # Cases where at least one expert is assigned (szakértők szerkesztése)
    szerkesztheto_cases = Case.query.filter(
        or_(
            and_(Case.expert_1 != None, Case.expert_1 != ''),
            and_(Case.expert_2 != None, Case.expert_2 != '')
        )
    ).order_by(Case.registration_time.desc()).all()

    return render_template(
        'szignal_cases.html',
        szignalando_cases=szignalando_cases,
        szerkesztheto_cases=szerkesztheto_cases
    )

@auth_bp.route('/szignal_cases/<int:case_id>/assign', methods=['GET', 'POST'])
@login_required
@roles_required('szignáló')
def assign_pathologist(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    uploads = UploadedFile.query.filter_by(case_id=case.id).all()
    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()

    # First expert: only "-- Válasszon --" as empty
    szakerto_choices = [('', '-- Válasszon --')] + [
        (u.username, u.screen_name or u.username) for u in szakerto_users
    ]

    # Get current selection (POST: from form, GET: from case object)
    expert_1_selected = request.form.get('expert_1') if request.method == 'POST' else (case.expert_1 or '')

    # Second expert: "-- Válasszon (opcionális)" as empty, exclude expert_1
    szakerto_choices_2 = [('', '-- Válasszon (opcionális)')] + [
        (u.username, u.screen_name or u.username)
        for u in szakerto_users if u.username != expert_1_selected
    ]

    if request.method == 'POST' and request.form.get('action') == 'upload':
        file = request.files.get('file')
        if file:
            fn = handle_file_upload(case, file)
            if fn:
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Database error: {e}")
                    flash("Valami hiba történt. Próbáld újra.", "danger")
                    return redirect(url_for('auth.assign_pathologist', case_id=case.id))
                flash('Fájl sikeresen feltöltve.', 'success')
        return redirect(url_for('auth.assign_pathologist', case_id=case.id))

    elif request.method == 'POST' and request.form.get('action') == 'assign':
        expert_1 = request.form.get('expert_1')
        expert_2 = request.form.get('expert_2') or None
        if not expert_1:
            flash("Szakértő 1 kitöltése kötelező.", 'warning')
            return redirect(url_for('auth.assign_pathologist', case_id=case.id))
        case.expert_1 = expert_1
        case.expert_2 = expert_2
        case.status = 'szignálva'
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for('auth.assign_pathologist', case_id=case.id))
        log_action(
            "Expert(s) assigned",
            f"{expert_1}" + (f", {expert_2}" if expert_2 else "") + f" for case {case.case_number}"
        )
        send_email(
            subject=f"Assigned to case {case.case_number}",
            recipients=[expert_1],
            body=f"You have been assigned as szakértő for case {case.case_number}."
        )
        flash('Szakértők sikeresen hozzárendelve.', 'success')
        return redirect(url_for('auth.szignal_cases'))

    changelog_entries = (
        ChangeLog.query
                 .filter_by(case_id=case.id)
                 .order_by(ChangeLog.timestamp.desc())
                 .limit(5)
                 .all()
    )
    return render_template(
        'assign_pathologist.html',
        case=case,
        szakerto_users=szakerto_users,
        szakerto_choices=szakerto_choices,
        szakerto_choices_2=szakerto_choices_2,
        changelog_entries=changelog_entries,
        uploads=uploads
    )

@auth_bp.route('/admin/users')
@login_required
@roles_required('admin')
def admin_users():
    users = User.query.order_by(User.username).all()
    return render_template('admin_users.html', users=users)

@auth_bp.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_user():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()
        if not username or not password or not role:
            flash("Minden mező kitöltése kötelező.", 'warning')
        elif User.query.filter_by(username=username).first():
            flash("Felhasználónév már foglalt.", 'warning')
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {e}")
                flash("Valami hiba történt. Próbáld újra.", "danger")
                return render_template('add_user.html')
            log_action("User created", f"{username} ({role})")
            flash("Felhasználó létrehozva.", 'success')
            return redirect(url_for('auth.admin_users'))
    return render_template('add_user.html')

@auth_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_user(user_id):

    user = db.session.get(User, user_id) or abort(404)

    if request.method == 'POST':
        old_data = (user.username, user.role, user.screen_name)
        user.username = request.form.get('username', user.username).strip()
        user.role = request.form.get('role', user.role).strip()
        user.screen_name = request.form.get('screen_name', user.screen_name).strip()  # Make sure to strip spaces

        password = request.form.get('password', '').strip()
        if password:
            user.set_password(password)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return render_template('edit_user.html', user=user, assigned_cases=assigned_cases)

        log_action("User edited", f"{old_data} → {(user.username, user.role, user.screen_name)}")
        flash("Felhasználó adatai frissítve.", 'success')
        return redirect(url_for('auth.admin_users'))

    assigned_cases = []
    if user.role in ('szakértő', 'leíró'):
        assigned_cases = Case.query.filter(
            or_(
                Case.expert_1 == user.username,
                Case.expert_2 == user.username,
                Case.describer == user.username
            )
        ).order_by(Case.registration_time.desc()).all()

    return render_template('edit_user.html', user=user, assigned_cases=assigned_cases)

@auth_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Saját magad nem törölheted.", 'warning')
    else:
        log_action("User deleted", f"{user.username}")
        db.session.delete(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            return redirect(url_for('auth.admin_users'))
        flash("Felhasználó törölve.", 'success')
    return redirect(url_for('auth.admin_users'))

@auth_bp.route('/admin/cases')
@login_required
@roles_required('admin')
def manage_cases():

    sort_by = request.args.get('sort_by', 'case_number')
    sort_order = request.args.get('sort_order', 'desc')

    # Map sorting keys to model columns
    sort_columns = {
        'case_number': Case.case_number,
        'deadline': Case.deadline,
    }

    order_col = sort_columns.get(sort_by, Case.case_number)

    if sort_order == 'asc':
        order = order_col.asc()
    else:
        order = order_col.desc()

    cases = Case.query.order_by(order).all()

    return render_template('admin_manage_cases.html',
                           cases=cases,
                           sort_by=sort_by,
                           sort_order=sort_order)

@auth_bp.route('/admin/cases/<int:case_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_case(case_id):

    case = db.session.get(Case, case_id) or abort(404)

    ChangeLog.query.filter_by(case_id=case.id).delete()

    log_action("Case deleted", f"{case.case_number}")
    db.session.delete(case)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return redirect(url_for('auth.manage_cases'))

    flash(f"Eset {case.case_number} törölve.", 'success')
    return redirect(url_for('auth.manage_cases'))

@auth_bp.route('/cases/<int:case_id>/add_note', methods=['POST'])
@login_required
def add_note_universal(case_id):
    data = request.get_json() or {}
    note_text = data.get('new_note', '').strip()

    if not note_text:
        current_app.logger.warning("Empty note submitted.")
        return jsonify({'error': 'Empty note'}), 400

    case = db.session.get(Case, case_id) or abort(404)
    ts = now_local().strftime('%Y-%m-%d %H:%M')
    author = current_user.screen_name or current_user.username
    entry = f"[{ts} – {author}] {note_text}"

    case.notes = (case.notes + "\n" if case.notes else "") + entry
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        flash("Valami hiba történt. Próbáld újra.", "danger")
        return jsonify({'error': 'DB error'}), 500

    html = f'<div class="alert alert-secondary py-2">{entry}</div>'
    current_app.logger.info(f"Returning note HTML: {html}")
    return jsonify({'html': html})

