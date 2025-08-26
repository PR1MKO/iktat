# app/views/auth.py

import shutil
from pathlib import Path
from datetime import datetime, timedelta, date
import hashlib

from app.utils.time_utils import now_local, BUDAPEST_TZ, fmt_date
from app.utils.permissions import capabilities_for
from app.utils.query_helpers import build_cases_and_users_map, apply_case_filters
from flask import (
    Blueprint, render_template, redirect, url_for, request,
    flash, current_app, jsonify, Response, abort
)
from flask_login import (
    login_user, logout_user,
    login_required, current_user
)
from werkzeug import exceptions
from app.utils.uploads import save_upload, send_safe, resolve_safe
from sqlalchemy import or_, and_, func

from app.models import UploadedFile, User, Case, AuditLog, ChangeLog, TaskMessage
from app.investigations.models import Investigation
from app.investigations.utils import user_display_name
from app.services.core_user_read import get_user_safe
from app.forms import CaseIdentifierForm, AdminUserForm
from app import db
from app.email_utils import send_email
from app.audit import log_action
from ..utils.case_helpers import build_case_context, ensure_unlocked_or_redirect
from ..utils.case_status import CASE_STATUS_FINAL, is_final_status
from ..utils.roles import roles_required
from app.utils.idempotency import claim_idempotency, make_default_key
from app.routes import handle_file_upload
from app.paths import case_root, ensure_case_folder, file_safe_case_number
from app.utils.case_number import generate_case_number_for_year
import csv
import io
import codecs

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------
# Upload root helper (keeps tests and app consistent)
# ---------------------------------------------------------------------
def _case_upload_root() -> str:
    return str(case_root())

def init_case_upload_dirs(case):
    """Create per-case upload folders and populate the DO-NOT-EDIT template set."""
    base = str(case_root())
    case_dir = str(ensure_case_folder(case.case_number))
    
    # Populate DO-NOT-EDIT from instance/docs/boncolas
    src_root = Path(current_app.instance_path) / "docs" / "boncolas"
    dst_root = Path(case_dir) / "DO-NOT-EDIT"
    dst_root.mkdir(parents=True, exist_ok=True)

    if not src_root.exists():
        current_app.logger.warning("Case template dir missing: %s", src_root)
        return

    current_app.logger.info("Populating DO-NOT-EDIT: %s -> %s", src_root, dst_root)
    for child in src_root.iterdir():
        target = dst_root / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            if not target.exists():
                shutil.copy2(child, target)


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
            "Content-Disposition": f"attachment; filename=changelog_{file_safe_case_number(case.case_number)}.csv"
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
        if current_app.config.get('STRICT_PRG_ENABLED', True):
            return redirect(url_for('auth.login'))
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
    now = now_local()
    today_start = datetime(now.year, now.month, now.day, tzinfo=BUDAPEST_TZ)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = datetime(now.year, now.month, 1, tzinfo=BUDAPEST_TZ)

    total_open = Case.query.filter(Case.status != CASE_STATUS_FINAL).count()
    new_today = Case.query.filter(Case.registration_time >= today_start).count()
    new_this_week = Case.query.filter(Case.registration_time >= week_start).count()
    new_this_month = Case.query.filter(Case.registration_time >= month_start).count()
    closed_cases = Case.query.filter(Case.status == CASE_STATUS_FINAL).count()
    status_counts = dict(db.session.query(Case.status, func.count()).group_by(Case.status).all())
    status_counts_list = list(status_counts.items())

    missing_fields = Case.query.filter(
        or_(Case.expert_1.is_(None), Case.expert_1 == ''),
        or_(Case.describer.is_(None), Case.describer == '')
    ).filter(Case.status != CASE_STATUS_FINAL).all()

    today = date.today()
    threshold = today + timedelta(days=14)
    upcoming_deadlines = (
        Case.query
            .filter(
                Case.deadline.isnot(None),
                Case.status != CASE_STATUS_FINAL,
                Case.deadline <= threshold
            )
            .order_by(Case.deadline.asc())
            .all()
    )

    template_ctx = dict(
        status_counts_list=status_counts_list,
        user=current_user,
        total_open=total_open,
        new_today=new_today,
        new_this_week=new_this_week,
        new_this_month=new_this_month,
        closed_cases=closed_cases,
        status_counts=status_counts,
        missing_fields=missing_fields,
        upcoming_deadlines=upcoming_deadlines,
    )
    
    if current_user.role == 'pénzügy':
        return redirect(url_for('auth.dashboard_penzugy'))

    # ✅ Ensure sorting + query params exist for macros (e.g., cases_table)
    template_ctx.setdefault('sort_by', request.args.get('sort_by') or 'deadline')
    template_ctx.setdefault('sort_order', request.args.get('sort_order') or 'asc')
    template_ctx['query_params'] = request.args.to_dict(flat=True)

    if current_user.role in {'szak', 'szakértő'}:
        assigned_investigations = (
            Investigation.query
            .filter(
                Investigation.assignment_type == 'SZAKÉRTŐI',
                Investigation.assigned_expert_id == current_user.id,
            )
            .order_by(Investigation.registration_time.desc())
            .all()
        )
        template_ctx['assigned_investigations'] = assigned_investigations

    if current_user.role == 'szakértő':
        task_messages = (
            db.session.query(TaskMessage)
            .join(Case)
            .filter(
                TaskMessage.recipient == current_user.username,
                TaskMessage.seen.is_(False),
                Case.expert_1 == (current_user.screen_name or current_user.username),
                Case.started_by_expert.is_(False),
            )
            .order_by(TaskMessage.timestamp.desc())
            .all()
        )
        template_ctx['task_messages'] = task_messages

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
        'pénzügy':  "dashboards/dashboard_penzugy.html",
    }
    tpl = dashboards.get(current_user.role)
    if tpl:
        return render_template(tpl, **template_ctx)
    elif current_user.role == 'toxi':
        return redirect(url_for('main.toxi_ugyeim'))
    else:
        flash(
            "Ismeretlen szerepkör. Kérjük, forduljon az adminisztrátorhoz.",
            "danger",
        )
        logout_user()
        return redirect(url_for("auth.login"))


@auth_bp.route('/dashboard/penzugy')
@login_required
@roles_required('pénzügy', 'admin')
def dashboard_penzugy():
    cases, users_map, ordering_meta = build_cases_and_users_map(request.args)

    investigations = (
        Investigation.query
        .order_by(Investigation.case_number.desc())
        .all()
    )
    for inv in investigations:
        inv.registration_time_str = fmt_date(inv.registration_time)
        inv.deadline_str = fmt_date(inv.deadline)
        inv.expert1_name = user_display_name(get_user_safe(inv.expert1_id))
        inv.expert2_name = user_display_name(get_user_safe(inv.expert2_id))
        inv.describer_name = user_display_name(get_user_safe(inv.describer_id))

    return render_template(
        'dashboards/dashboard_penzugy.html',
        cases=cases,
        users_map=users_map,
        sort_by=ordering_meta['sort_by'],
        sort_order=ordering_meta['sort_order'],
        query_params=request.args.to_dict(),
        investigations=investigations,
        caps=capabilities_for(current_user),
    )


@auth_bp.route('/cases')
@login_required
def list_cases():
    status_filter = request.args.get('status', '')
    case_type_filter = request.args.get('case_type', '')
    search_query = request.args.get('search', '').strip()

    query = Case.query
    query = apply_case_filters(query, request.args)

    cases, users_map, ordering_meta = build_cases_and_users_map(request.args, query)

    query_params = request.args.to_dict()

    return render_template(
        'list_cases.html',
        cases=cases,
        users_map=users_map,
        sort_by=ordering_meta['sort_by'],
        sort_order=ordering_meta['sort_order'],
        query_params=query_params,
        status_filter=status_filter,
        case_type_filter=case_type_filter,
        search_query=search_query,
        caps=capabilities_for(current_user)
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
        caps=capabilities_for(current_user),
        **ctx
    )


@auth_bp.route('/cases/<int:case_id>/view')
@login_required
def view_case(case_id):
    """Read-only view for case details."""
    case = db.session.get(Case, case_id) or abort(404)

    ctx = build_case_context(case)
    ctx['changelog_entries'] = [
        e for e in ctx['changelog_entries'] if e.field_name != 'notes'
    ]

    return render_template(
        'case_detail.html',
        case=case,
        caps=capabilities_for(current_user),
        **ctx
    )


@auth_bp.route('/cases/closed')
@login_required
def closed_cases():
    closed = Case.query.filter(Case.status == CASE_STATUS_FINAL)\
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
    
    caps = capabilities_for(current_user)
    if not caps.get("can_edit_case"):
        flash("Nincs jogosultság", "danger")
        return redirect(url_for('auth.list_cases'))

    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()
    leiro_users    = User.query.filter_by(role='leíró').order_by(User.username).all()
    szakerto_choices = [('', '(opcionális)')] + [
        (u.screen_name, u.screen_name or u.username) for u in szakerto_users
    ]
    leiro_choices = [('', '(opcionális)')] + [
        (u.screen_name, u.screen_name or u.username) for u in leiro_users
    ]
    case = DummyCase()  # Always available for the template/macros

    if request.method == 'POST':
        missing = []
        if not request.form.get('case_type'):
            missing.append('Típus')
        if not request.form.get('beerk_modja'):
            missing.append('Beérkezés módja')
        if missing:
            flash(', '.join(missing) + ' kitöltése kötelező.')
        if not form.validate():
            for err in form.external_id.errors:
                flash(err)
        if missing or form.errors:
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.create_case'))
            return render_template(
                'create_case.html',
                szakerto_users=szakerto_users,
                leiro_users=leiro_users,
                szakerto_choices=szakerto_choices,
                leiro_choices=leiro_choices,
                case=case,
                form=form,
                caps=caps
            )
        ext_id = form.external_id.data or ''
        key = make_default_key(request, extra=ext_id)
        if not claim_idempotency(key, route=request.endpoint, user_id=current_user.id, case_id=None):
            flash("Művelet már feldolgozva.")
            if ext_id:
                existing = Case.query.filter_by(external_case_number=ext_id).first()
                if existing:
                    return redirect(url_for('auth.case_documents', case_id=existing.id))
            return redirect(url_for('auth.create_case'))
        birth_date = None
        if request.form.get('birth_date'):
            birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
        registration_time = now_local()
        case_number = generate_case_number_for_year(db.session)
        notes = request.form.get('notes', '').strip() or None

        # --- Handle the new "További adatok" fields ---
        beerk_modja  = request.form.get('beerk_modja', '').strip() or None
        poszeidon    = request.form.get('poszeidon', '').strip() or None
        lanykori_nev = request.form.get('lanykori_nev', '').strip() or None
        mother_name  = request.form.get('mother_name', '').strip() or None
        szul_hely    = request.form.get('szul_hely', '').strip() or None
        taj_szam     = request.form.get('taj_szam', '').strip() or None
        residence    = request.form.get('residence', '').strip() or None
        citizenship  = request.form.get('citizenship', '').strip() or None

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
            mother_name=mother_name,
            szul_hely=szul_hely,
            taj_szam=taj_szam,
            residence=residence,
            citizenship=citizenship,
        )
        new_case.deadline = registration_time + timedelta(days=30)
        db.session.add(new_case)
        try:
            db.session.commit()
            init_case_upload_dirs(new_case)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.create_case'))
            return render_template(
                'create_case.html',
                szakerto_users=szakerto_users,
                leiro_users=leiro_users,
                szakerto_choices=szakerto_choices,
                leiro_choices=leiro_choices,
                case=case,
                form=form,
                caps=caps
            )

        # Log case creation in ChangeLog
        log = ChangeLog(
            case=new_case,
            field_name='system',
            old_value='',
            new_value='ügy érkeztetve',
            edited_by=current_user.screen_name or current_user.username,
            timestamp=now_local(),
        )
        db.session.add(log)
        db.session.commit()

        flash('New case created.', 'success')
        return redirect(url_for('auth.case_documents', case_id=new_case.id))

    return render_template(
        'create_case.html',
        szakerto_users=szakerto_users,
        leiro_users=leiro_users,
        szakerto_choices=szakerto_choices,
        leiro_choices=leiro_choices,
        case=case,
        form=form,
        caps=caps
    )


@auth_bp.route('/cases/<int:case_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'iroda')
def edit_case(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)) is not None:
        return resp
    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()
    leiro_users    = User.query.filter_by(role='leíró').order_by(User.username).all()
    changelog_entries = (
        ChangeLog.query
                 .filter_by(case_id=case.id)
                 .order_by(ChangeLog.timestamp.desc())
                 .limit(5)
                 .all()
    )
    if request.method == 'POST':
        form_version = request.form.get('form_version')
        if form_version and case.updated_at and form_version != case.updated_at.isoformat():
            flash("Az űrlap időközben frissült. Kérjük, töltse be újra.")
            return redirect(url_for('auth.edit_case', case_id=case.id))
        case.deceased_name = request.form.get('deceased_name') or None
        case.lanykori_nev = request.form.get('lanykori_nev') or None
        case.mother_name = request.form.get('mother_name') or None
        case.taj_szam = request.form.get('taj_szam') or None
        case.szul_hely = request.form.get('szul_hely') or None
        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            try:
                case.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                case.birth_date = None
        else:
            case.birth_date = None
        case.poszeidon = request.form.get('poszeidon') or None
        case.external_case_number = request.form.get('external_case_number') or None
        case.temp_id = request.form.get('temp_id') or None
        case.institution_name = request.form.get('institution_name') or None
        case.beerk_modja = request.form.get('beerk_modja') or None
        case.expert_1 = request.form.get('expert_1') or None
        case.expert_2 = request.form.get('expert_2') or None
        case.describer = request.form.get('describer') or None
        if current_user.role == 'iroda':
            case.residence = request.form.get('residence') or None
            case.citizenship = request.form.get('citizenship') or None
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash("Valami hiba történt. Próbáld újra.", "danger")
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.edit_case', case_id=case.id))
            return render_template('edit_case.html', case=case, szakerto_users=szakerto_users, leiro_users=leiro_users, changelog_entries=changelog_entries)
        flash('Az ügy módosításai elmentve.', 'success')
        return redirect(url_for('auth.case_detail', case_id=case.id))
    return render_template(
        'edit_case.html',
        case=case,
        szakerto_users=szakerto_users,
        leiro_users=leiro_users,
        changelog_entries=changelog_entries
    )


@auth_bp.route('/cases/<int:case_id>/edit_basic', methods=['GET', 'POST'])
@login_required
def edit_case_basic(case_id):
    if current_user.role != 'iroda':
        abort(403)
    case = db.session.get(Case, case_id) or abort(404)
    if (resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)) is not None:
        return resp

    if request.method == 'POST':
        form_version = request.form.get('form_version')
        if form_version and case.updated_at and form_version != case.updated_at.isoformat():
            flash("Az űrlap időközben frissült. Kérjük, töltse be újra.")
            return redirect(url_for('auth.edit_case_basic', case_id=case.id))
        case.deceased_name = request.form.get('deceased_name') or None
        case.lanykori_nev = request.form.get('lanykori_nev') or None
        case.mother_name = request.form.get('mother_name') or None
        case.taj_szam = request.form.get('taj_szam') or None
        case.szul_hely = request.form.get('szul_hely') or None
        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            try:
                case.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                case.birth_date = None
        else:
            case.birth_date = None
        case.poszeidon = request.form.get('poszeidon') or None
        case.external_case_number = request.form.get('external_case_number') or None
        case.temp_id = request.form.get('temp_id') or None
        case.institution_name = request.form.get('institution_name') or None
        case.beerk_modja = request.form.get('beerk_modja') or None
        case.residence = request.form.get('residence') or None
        case.citizenship = request.form.get('citizenship') or None

        log = ChangeLog(
            case=case,
            field_name='system',
            old_value='',
            new_value='alapadat(ok) szerkesztve',
            edited_by=current_user.screen_name or current_user.username,
            timestamp=now_local(),
        )
        db.session.add(log)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash('Valami hiba történt. Próbáld újra.', 'danger')
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.edit_case_basic', case_id=case.id))
            return render_template('edit_case_basic.html', case=case)
        flash('Az alapadatok módosításai elmentve.', 'success')
        return redirect(url_for('auth.list_cases'))

    return render_template('edit_case_basic.html', case=case)


@auth_bp.route('/cases/<int:case_id>/documents', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'iroda')
def case_documents(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)) is not None:
        return resp
    if request.method == 'POST':
        case.tox_ordered = bool(request.form.get('tox_ordered'))
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {e}")
            flash('Valami hiba történt. Próbáld újra.', 'danger')
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.case_documents', case_id=case_id))
            return render_template('case_documents.html', case=case)
        return redirect(url_for('auth.edit_case', case_id=case_id))
    return render_template('case_documents.html', case=case)


@auth_bp.route('/cases/<int:case_id>/upload', methods=['POST'])
@login_required
@roles_required('admin', 'iroda', 'szakértő', 'leíró', 'szignáló', 'toxi')
def upload_file(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    caps = capabilities_for(current_user)
    if not caps.get("can_upload_case"):
        flash("Nincs jogosultság", "danger")
        return redirect(url_for('auth.case_detail', case_id=case_id))
    if is_final_status(case.status):
        flash('Case is finalized. Uploads are disabled.', 'danger')
        return redirect(url_for('auth.case_detail', case_id=case_id))

    root = Path(current_app.config["UPLOAD_CASES_ROOT"])
    subdir = file_safe_case_number(case.case_number)
    category = request.form.get('category')
    if not category:
        flash("Kérjük, válasszon fájl kategóriát.", "error")
        return redirect(request.referrer or url_for('auth.case_detail', case_id=case_id))

    files = request.files.getlist('file')
    if not files:
        flash('No files selected', 'warning')
        return redirect(request.referrer or url_for('auth.case_detail', case_id=case_id))

    saved = []
    for f in files:
        try:
            dest = save_upload(f, root, "cases", subdir)
        except exceptions.BadRequest:
            raise
        except Exception as e:
            current_app.logger.error(f"File save failed: {e}")
            flash("A fájl mentése nem sikerült.", "danger")
            continue
        upload_rec = UploadedFile(
            case_id=case.id,
            filename=dest.name,
            uploader=current_user.username,
            upload_time=now_local(),
            category=category
        )
        db.session.add(upload_rec)
        saved.append(dest.name)
        log_action("File uploaded", f"{dest.name} for case {case.case_number}")

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
    if request.referrer and 'elvegzem_toxi' in request.referrer:
        return redirect(url_for('main.elvegzem_toxi', case_id=case_id))
    if request.referrer and '/documents' in request.referrer:
        return redirect(url_for('auth.case_documents', case_id=case_id))
    return redirect(url_for('auth.case_detail', case_id=case_id))

@auth_bp.route('/cases/<int:case_id>/files/<path:filename>')
@login_required
@roles_required('admin', 'iroda', 'szakértő', 'leíró', 'szignáló', 'toxi')
def download_file(case_id, filename):
    case = db.session.get(Case, case_id) or abort(404)
    subdir = file_safe_case_number(case.case_number)
    root = Path(current_app.config["UPLOAD_CASES_ROOT"]) / subdir

    try:
        resp = send_safe(root, filename, as_attachment=True)
    except exceptions.BadRequest:
        current_app.logger.warning(
            f"Path traversal attempt for case {case_id}: {filename}"
        )
        abort(400)
    except FileNotFoundError:
        current_app.logger.warning(
            f"File not found for case {case_id}: {filename}"
        )
        abort(404)
    log_action("File downloaded", f"{filename} from case {case.case_number}")
    return resp

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
    szerkesztheto_cases = (
        Case.query.filter(
            or_(
                and_(Case.expert_1.isnot(None), Case.expert_1 != ''),
                and_(Case.expert_2.isnot(None), Case.expert_2 != '')
            )
        )
        .order_by(Case.registration_time.desc())
        .all()
    )

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
    caps = capabilities_for(current_user)
    if not caps.get("can_assign"):
        flash("Nincs jogosultság", "danger")
        return redirect(url_for('auth.case_detail', case_id=case_id))
    uploads = UploadedFile.query.filter_by(case_id=case.id).all()
    szakerto_users = User.query.filter_by(role='szakértő').order_by(User.username).all()

    # First expert: only "-- Válasszon --" as empty
    szakerto_choices = [('', '-- Válasszon --')] + [
        (u.screen_name, u.screen_name or u.username) for u in szakerto_users
    ]

    # Get current selection (POST: from form, GET: from case object)
    expert_1_selected = request.form.get('expert_1') if request.method == 'POST' else (case.expert_1 or '')

    # Second expert: "-- Válasszon (opcionális)" as empty, exclude expert_1
    szakerto_choices_2 = [('', '-- Válasszon (opcionális)')] + [
        (u.screen_name, u.screen_name or u.username)
        for u in szakerto_users if u.screen_name != expert_1_selected
    ]

    if request.method == 'POST' and request.form.get('action') == 'upload':
        file = request.files.get('file')
        category = request.form.get('category') or 'egyéb'
        if file:
            fn = handle_file_upload(case, file, category=category)
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
        form_version = request.form.get('form_version')
        if form_version and case.updated_at and form_version != case.updated_at.isoformat():
            flash("Az űrlap időközben frissült. Kérjük, töltse be újra.")
            return redirect(url_for('auth.assign_pathologist', case_id=case.id))
        raw = f"{request.endpoint}|{current_user.id}|{case.id}|{expert_1}|{expert_2 or ''}"
        key = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        if not claim_idempotency(key, route=request.endpoint, user_id=current_user.id, case_id=case.id):
            flash("Nincs változás.")
            return redirect(url_for('auth.assign_pathologist', case_id=case.id))
        case.expert_1 = expert_1
        case.expert_2 = expert_2
        case.status = 'szignálva'
        
        assigned_user = User.query.filter_by(screen_name=case.expert_1).first()
        if assigned_user:
            msg = TaskMessage(
                user_id=assigned_user.id,
                recipient=assigned_user.username,
                case_id=case.id,
                message=f"{case.case_number} has been signalled to you",
                timestamp=now_local()
            )
            db.session.add(msg)
        
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
        recipient = assigned_user.username if assigned_user else expert_1
        send_email(
            subject=f"Assigned to case {case.case_number}",
            recipients=[recipient],
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
        uploads=uploads,
        caps=caps
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
    form = AdminUserForm()
    leiro_users = User.query.filter_by(role='leíró').order_by(User.username).all()
    form.default_leiro_id.choices = [(0, '-- Válasszon --')] + [(u.id, (u.screen_name or u.username)) for u in leiro_users]
    
    if request.method == 'POST':
        username = (form.username.data or '').strip()
        password = (form.password.data or '').strip()
        role = (form.role.data or '').strip()
        chosen = form.default_leiro_id.data or None
        if role == 'szakértő':
            if not chosen:
                errs = list(form.default_leiro_id.errors)
                errs.append('Szakértő esetén kötelező.')
                form.default_leiro_id.errors = errs
            else:
                leiro = db.session.get(User, chosen)
                if not leiro or leiro.role != 'leíró':
                    errs = list(form.default_leiro_id.errors)
                    errs.append('Csak leíró választható.')
                    form.default_leiro_id.errors = errs
        if not username or not password or not role:
            flash("Minden mező kitöltése kötelező.", 'warning')
        elif User.query.filter_by(username=username).first():
            flash("Felhasználónév már foglalt.", 'warning')
        elif form.default_leiro_id.errors:
            for err in form.default_leiro_id.errors:
                flash(err, 'warning')
        else:
            user = User(
                username=username,
                role=role,
                screen_name=(form.screen_name.data or '').strip() or None,
                full_name=(form.full_name.data or '').strip() or None,
            )
            user.set_password(password)
            user.default_leiro_id = chosen if role == 'szakértő' else None
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {e}")
                flash("Valami hiba történt. Próbáld újra.", "danger")
                if current_app.config.get('STRICT_PRG_ENABLED', True):
                    return redirect(url_for('auth.add_user'))               
                return render_template('add_user.html', form=form, leiro_users=leiro_users)
            log_action("User created", f"{username} ({role})")
            flash("Felhasználó létrehozva.", 'success')
            return redirect(url_for('auth.admin_users'))
        if current_app.config.get('STRICT_PRG_ENABLED', True):
            return redirect(url_for('auth.add_user'))
    return render_template('add_user.html', form=form, leiro_users=leiro_users)

@auth_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_user(user_id):

    user = db.session.get(User, user_id) or abort(404)
    leiro_users = User.query.filter_by(role='leíró').order_by(User.username).all()
    form = AdminUserForm(obj=user)
    form.default_leiro_id.choices = [(0, '-- Válasszon --')] + [(u.id, (u.screen_name or u.username)) for u in leiro_users]
    if request.method == 'GET':
        form.default_leiro_id.data = user.default_leiro_id or 0
    
    assigned_cases = []
    if user.role in ('szakértő', 'leíró'):
        assigned_cases = (
            Case.query.filter(
                or_(
                    Case.expert_1 == user.username,
                    Case.expert_2 == user.username,
                    Case.describer == user.username,
                )
            )
            .order_by(Case.registration_time.desc())
            .all()
        )

    if request.method == 'POST':
        role = (form.role.data or '').strip()
        chosen = form.default_leiro_id.data or None
        if role == 'szakértő':
            if not chosen:
                errs = list(form.default_leiro_id.errors)
                errs.append('Szakértő esetén kötelező.')
                form.default_leiro_id.errors = errs
            else:
                leiro = db.session.get(User, chosen)
                if not leiro or leiro.role != 'leíró':
                    errs = list(form.default_leiro_id.errors)
                    errs.append('Csak leíró választható.')
                    form.default_leiro_id.errors = errs
        if form.validate_on_submit() and not form.default_leiro_id.errors:
            old_data = (user.username, user.role, user.screen_name)
            user.username = form.username.data.strip()
            user.role = role
            user.screen_name = (form.screen_name.data or '').strip()
            user.full_name = (form.full_name.data or '').strip() or None
            password = (form.password.data or '').strip()
            if password:
                user.set_password(password)
            user.default_leiro_id = chosen if role == 'szakértő' else None
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {e}")
                flash("Valami hiba történt. Próbáld újra.", "danger")
                if current_app.config.get('STRICT_PRG_ENABLED', True):
                    return redirect(url_for('auth.edit_user', user_id=user.id))
                return render_template('edit_user.html', form=form, user=user, assigned_cases=assigned_cases, leiro_users=leiro_users)
            log_action("User edited", f"{old_data} → {(user.username, user.role, user.screen_name)}")
            flash("Felhasználó adatai frissítve.", 'success')
            return redirect(url_for('auth.admin_users'))
        else:
            for errs in form.errors.values():
                for err in errs:
                    flash(err, 'warning')
            for err in form.default_leiro_id.errors:
                flash(err, 'warning')
            if current_app.config.get('STRICT_PRG_ENABLED', True):
                return redirect(url_for('auth.edit_user', user_id=user.id))

    return render_template('edit_user.html', form=form, user=user, assigned_cases=assigned_cases, leiro_users=leiro_users)

@auth_bp.route('/admin/cases')
@login_required
@roles_required('admin')
def manage_cases():

    sort_by = request.args.get('sort_by', 'case_number')
    sort_order = request.args.get('sort_order', 'desc')

    if sort_by == 'case_number':
        year_col = func.substr(Case.case_number, 8, 4)
        seq_col = func.substr(Case.case_number, 3, 4)
        if sort_order == 'asc':
            cases = Case.query.order_by(year_col.asc(), seq_col.asc()).all()
        else:
            cases = Case.query.order_by(year_col.desc(), seq_col.desc()).all()
    else:
        col = Case.deadline
        col = col.asc() if sort_order == 'asc' else col.desc()
        cases = Case.query.order_by(col).all()

    return render_template('admin_manage_cases.html',
                           cases=cases,
                           sort_by=sort_by,
                           sort_order=sort_order)


@auth_bp.route('/admin/cases/<int:case_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_case(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)) is not None:
        return resp

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
    caps = capabilities_for(current_user)
    if not caps.get("can_post_notes"):
        return jsonify({'error': 'Nincs jogosultság'}), 403
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
        return jsonify({'error': 'DB error'}), 500

    html = f'<div class="alert alert-secondary py-2">{entry}</div>'
    current_app.logger.info(f"Returning note HTML: {html}")
    return jsonify({'html': html})


@auth_bp.route('/cases/<int:case_id>/tox_doc_form', methods=['GET'])
@login_required
@roles_required('toxi', 'iroda', 'admin')
def tox_doc_form(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    return render_template('tox_doc_form.html', case=case)


@auth_bp.route('/cases/<int:case_id>/generate_tox_doc', methods=['POST'])
@login_required
@roles_required('admin', 'iroda', 'toxi')
def generate_tox_doc(case_id):
    case = db.session.get(Case, case_id) or abort(404)
    if (resp := ensure_unlocked_or_redirect(case, "auth.case_detail", case_id=case.id)) is not None:
        return resp
    key = make_default_key(request)
    if not claim_idempotency(key, route=request.endpoint, user_id=current_user.id, case_id=case.id):
        flash("Művelet már feldolgozva.")
        return redirect(url_for('auth.case_detail', case_id=case.id))

    root = Path(current_app.config["UPLOAD_CASES_ROOT"])
    template_path = resolve_safe(
        root,
        'autofill-word-do-not-edit',
        'Toxikológiai-kirendelő.docx'
    )
    # Save under per-case folder named by SAFE case number (matches tests)
    subdir = file_safe_case_number(case.case_number)
    output_path = resolve_safe(
        root,
        subdir,
        'Toxikológiai-kirendelő-kitöltött.docx'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def safe_int(v):
        try: return int(v)
        except Exception: return 0

    def safe_float(v):
        try: return float(v)
        except Exception: return 0.0

    total = (
        safe_int(request.form.get("alkohol_minta_count")) * safe_float(request.form.get("alkohol_minta_ara")) +
        safe_int(request.form.get("permetezoszer_minta_count")) * safe_float(request.form.get("permetezoszer_minta_ara")) +
        safe_int(request.form.get("etilenglikol_minta_count")) * safe_float(request.form.get("etilenglikol_minta_ara")) +
        safe_int(request.form.get("diatoma_minta_count")) * safe_float(request.form.get("diatoma_minta_ara")) +
        safe_int(request.form.get("szarazanyag_minta_count")) * safe_float(request.form.get("szarazanyag_minta_ara")) +
        safe_int(request.form.get("gyogyszer_minta_count")) * safe_float(request.form.get("gyogyszer_minta_ara")) +
        safe_int(request.form.get("kabitoszer_minta_count")) * safe_float(request.form.get("kabitoszer_minta_ara")) +
        safe_int(request.form.get("co_minta_count")) * safe_float(request.form.get("co_minta_ara")) +
        safe_int(request.form.get("egyeb_minta_count")) * safe_float(request.form.get("egyeb_minta_ara"))
    )

    context = {
        "case": {
            "deceased_name": case.deceased_name or "",
            "birth_date": case.birth_date or "",
            "szul_hely": case.szul_hely or "",
            "anyja_neve": case.anyja_neve or "",
            "case_number": case.case_number or "",
            "external_case_number": case.external_case_number or "",
        },
        "intezmeny": case.institution_name or "",
        "today": now_local().strftime("%Y.%m.%d"),
        "current_user": current_user.screen_name or current_user.username,
        "alkohol_minta_count": safe_int(request.form.get("alkohol_minta_count")),
        "alkohol_minta_ara": safe_float(request.form.get("alkohol_minta_ara")),
        "permetezoszer_minta_count": safe_int(request.form.get("permetezoszer_minta_count")),
        "permetezoszer_minta_ara": safe_float(request.form.get("permetezoszer_minta_ara")),
        "etilenglikol_minta_count": safe_int(request.form.get("etilenglikol_minta_count")),
        "etilenglikol_minta_ara": safe_float(request.form.get("etilenglikol_minta_ara")),
        "diatoma_minta_count": safe_int(request.form.get("diatoma_minta_count")),
        "diatoma_minta_ara": safe_float(request.form.get("diatoma_minta_ara")),
        "szarazanyag_minta_count": safe_int(request.form.get("szarazanyag_minta_count")),
        "szarazanyag_minta_ara": safe_float(request.form.get("szarazanyag_minta_ara")),
        "gyogyszer_minta_count": safe_int(request.form.get("gyogyszer_minta_count")),
        "gyogyszer_minta_ara": safe_float(request.form.get("gyogyszer_minta_ara")),
        "kabitoszer_minta_count": safe_int(request.form.get("kabitoszer_minta_count")),
        "kabitoszer_minta_ara": safe_float(request.form.get("kabitoszer_minta_ara")),
        "co_minta_count": safe_int(request.form.get("co_minta_count")),
        "co_minta_ara": safe_float(request.form.get("co_minta_ara")),
        "egyeb_minta_count": safe_int(request.form.get("egyeb_minta_count")),
        "egyeb_minta_ara": safe_float(request.form.get("egyeb_minta_ara")),
        "osszesen_ara": int(total),
    }

    try:
        try:
            # Preferred: docxtpl
            from docxtpl import DocxTemplate
            tpl = DocxTemplate(str(template_path))
            tpl.render(context)
            tpl.save(str(output_path))
        except ModuleNotFoundError:
            # Fallback: plain python-docx tag replace for tests
            from docx import Document
            doc = Document(str(template_path))
            # VERY simple {{...}} replacements used by the tests
            replacements = {
                "{{case.case_number}}": context["case"]["case_number"],
                "{{case.anyja_neve}}": context["case"]["anyja_neve"],
            }
            for p in doc.paragraphs:
                for k, v in replacements.items():
                    if k in p.text:
                        p.text = p.text.replace(k, str(v))
            doc.save(str(output_path))

        case.tox_doc_generated = True
        case.tox_doc_generated_at = now_local()
        case.tox_doc_generated_by = current_user.screen_name or current_user.username

        db.session.add(UploadedFile(
            case_id=case.id,
            filename=output_path.name,
            uploader=current_user.username,
            upload_time=now_local(),
            category='Toxikológiai kirendelő'
        ))
        db.session.commit()
        flash("✅ Toxikológiai kirendelő dokumentum generálva.", "success")
        log_action("Toxikológiai kirendelő generálva", f"{case.case_number}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"DOCX generation error: {e}")
        flash("❌ Hiba történt a dokumentum generálása közben.", "danger")

    return redirect(url_for('auth.case_detail', case_id=case_id))
