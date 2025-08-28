from sqlalchemy import or_, and_, func
from app.utils.time_utils import now_local
from app.models import Case, User
from app import db
from .dates import attach_case_dates


def apply_case_filters(query, request_args):
    """Apply status, type, and search filters to the query based on request args."""
    status_filter = request_args.get('status', '')
    case_type_filter = request_args.get('case_type', '')
    search_query = request_args.get('search', '').strip()

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
    return query


def build_cases_and_users_map(request_args, base_query=None):
    """
    Returns (cases, users_map, ordering_meta) applying the same sort semantics as list_cases.
    Does NOT apply status/type/search filters unless request_args includes them.
    """
    q = base_query or Case.query
    sort_by = request_args.get('sort_by', 'case_number')
    sort_order = request_args.get('sort_order', 'desc')

    # order_by (case_number via substr, else deadline)
    if sort_by == 'case_number':
        year_col = func.substr(Case.case_number, 8, 4)
        seq_col = func.substr(Case.case_number, 3, 4)
        ordering = [year_col.desc(), seq_col.desc()] if sort_order == 'desc' else [year_col.asc(), seq_col.asc()]
    else:
        col = Case.deadline
        ordering = [col.desc() if sort_order == 'desc' else col.asc()]

    # split expired vs active to surface overdue first
    now = now_local()
    expired_cases = q.filter(Case.deadline < now).order_by(*ordering).all()
    active_cases = q.filter(or_(Case.deadline >= now, Case.deadline.is_(None))).order_by(*ordering).all()
    cases = expired_cases + active_cases
    for case in cases:
        attach_case_dates(case)

    # users map
    users = User.query.all()
    users_map = {(u.screen_name or u.username): u for u in users}

    return cases, users_map, {"sort_by": sort_by, "sort_order": sort_order}