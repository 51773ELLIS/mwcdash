from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from models import db, User, Entry, Settings, Worker
from config import get_config
from calendar import monthrange
import os
import json
import math

app = Flask(__name__)
app.config.from_object(get_config())

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))


def _count_weekdays(start_date, end_date):
    """Count weekdays (Mon-Fri) between two dates inclusive."""
    if start_date > end_date:
        return 0
    delta = end_date - start_date
    weekday_count = 0
    for days in range(delta.days + 1):
        current_day = start_date + timedelta(days=days)
        if current_day.weekday() < 5:  # Monday=0 ... Sunday=6
            weekday_count += 1
    return weekday_count


def get_month_workday_stats(reference_date=None):
    """Return total, passed, and remaining nominal workdays for the month of reference_date."""
    if reference_date is None:
        reference_date = date.today()
    month_start = date(reference_date.year, reference_date.month, 1)
    last_day = monthrange(reference_date.year, reference_date.month)[1]
    month_end = date(reference_date.year, reference_date.month, last_day)
    total_workdays = _count_weekdays(month_start, month_end)
    remaining_workdays = _count_weekdays(reference_date, month_end)
    workdays_passed = max(total_workdays - remaining_workdays, 0)
    return {
        'total': total_workdays,
        'passed': workdays_passed,
        'remaining': remaining_workdays
    }


def init_db():
    """Initialize database, run migrations, and create default user if needed"""
    with app.app_context():
        # Run migrations to ensure database schema is up to date
        try:
            from flask_migrate import upgrade
            upgrade()
            print("Database migrations completed successfully.")
        except Exception as e:
            print(f"Migration note: {e}")
            # If migrations haven't been initialized yet, create tables
            # This happens on first run before migrations are set up
            try:
                db.create_all()
                print("Database tables created (first run).")
            except Exception as create_error:
                print(f"Error creating tables: {create_error}")
        
        # Create default user if no users exist
        if User.query.count() == 0:
            default_user = User(username='ellis')
            default_user.set_password('changeme')  # Change this in production!
            db.session.add(default_user)
            
            # Create default settings
            default_settings = Settings(
                user_id=default_user.id,
                tax_percent=25.0,
                reinvest_percent=20.0,
                take_home_percent=55.0,
                currency_symbol='$',
                daily_revenue_goal=0.0,
                monthly_revenue_goal=0.0,
                monthly_take_home_goal=0.0,
                target_days_per_month=0,
                profit_quota=0.0,
                loss_quota=0.0
            )
            db.session.add(default_settings)
            db.session.commit()
            print("Default user created: username='ellis', password='changeme'")


@app.route('/')
def index():
    """Redirect to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with analytics"""
    # Get user settings
    settings = Settings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = Settings(
            user_id=current_user.id,
            tax_percent=0.0,
            reinvest_percent=0.0,
            take_home_percent=100.0,
            currency_symbol='$',
            daily_revenue_goal=0.0,
            monthly_revenue_goal=0.0,
            monthly_take_home_goal=0.0,
            profit_quota=0.0,
            loss_quota=0.0
        )
        db.session.add(settings)
        db.session.commit()
    else:
        # Ensure goal fields exist (for existing databases before migration)
        if not hasattr(settings, 'daily_revenue_goal'):
            settings.daily_revenue_goal = 0.0
        if not hasattr(settings, 'monthly_revenue_goal'):
            settings.monthly_revenue_goal = 0.0
        if not hasattr(settings, 'profit_quota'):
            settings.profit_quota = 0.0
        if not hasattr(settings, 'loss_quota'):
            settings.loss_quota = 0.0
        # Check if values are None and set defaults
        if settings.daily_revenue_goal is None:
            settings.daily_revenue_goal = 0.0
        if settings.monthly_revenue_goal is None:
            settings.monthly_revenue_goal = 0.0
        if settings.monthly_take_home_goal is None:
            settings.monthly_take_home_goal = 0.0
        if not hasattr(settings, 'target_days_per_month') or settings.target_days_per_month is None:
            settings.target_days_per_month = 0
        if settings.profit_quota is None:
            settings.profit_quota = 0.0
        if settings.loss_quota is None:
            settings.loss_quota = 0.0
    
    # Get worker filter
    worker_filter = request.args.get('worker', 'all')
    
    # Calculate totals
    total_revenue_query = db.session.query(func.sum(Entry.revenue)).filter_by(user_id=current_user.id)
    total_hours_query = db.session.query(func.sum(Entry.hours)).filter_by(user_id=current_user.id)
    entry_count_query = Entry.query.filter_by(user_id=current_user.id)
    
    if worker_filter != 'all':
        total_revenue_query = total_revenue_query.filter(Entry.worker_name == worker_filter)
        total_hours_query = total_hours_query.filter(Entry.worker_name == worker_filter)
        entry_count_query = entry_count_query.filter(Entry.worker_name == worker_filter)
    
    total_revenue = total_revenue_query.scalar() or 0.0
    total_hours = total_hours_query.scalar() or 0.0
    entry_count = entry_count_query.count()
    
    # Calculate averages
    avg_daily_revenue = total_revenue / entry_count if entry_count > 0 else 0.0
    avg_hours_per_day = total_hours / entry_count if entry_count > 0 else 0.0
    
    # Calculate amounts based on percentages
    tax_amount = total_revenue * (settings.tax_percent / 100)
    reinvest_amount = total_revenue * (settings.reinvest_percent / 100)
    take_home_amount = total_revenue * (settings.take_home_percent / 100)
    
    # Calculate additional metrics
    avg_daily_take_home = take_home_amount / entry_count if entry_count > 0 else 0.0
    avg_hourly_rate = total_revenue / total_hours if total_hours > 0 else 0.0
    
    # Advanced analytics
    best_day = None
    best_day_revenue = 0.0
    best_day_hours = 0.0
    
    # Get worker breakdown
    worker_stats = {}
    worker_entries = Entry.query.filter_by(user_id=current_user.id).all()
    if worker_filter != 'all':
        worker_entries = [e for e in worker_entries if e.worker_name == worker_filter]
    
    for entry in worker_entries:
        worker_name = entry.worker_name or 'Unassigned'
        if worker_name not in worker_stats:
            worker_stats[worker_name] = {'revenue': 0.0, 'hours': 0.0, 'count': 0}
        worker_stats[worker_name]['revenue'] += entry.revenue
        worker_stats[worker_name]['hours'] += entry.hours
        worker_stats[worker_name]['count'] += 1
        
        # Track best day
        if entry.revenue > best_day_revenue:
            best_day_revenue = entry.revenue
            best_day_hours = entry.hours
            best_day = entry.date
    
    # Calculate trends (compare last 30 days vs previous 30 days)
    if entry_count > 0:
        end_date = date.today()
        recent_start = end_date - timedelta(days=29)
        previous_start = recent_start - timedelta(days=30)
        
        recent_query = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= recent_start,
            Entry.date <= end_date
        )
        previous_query = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= previous_start,
            Entry.date < recent_start
        )
        
        if worker_filter != 'all':
            recent_query = recent_query.filter(Entry.worker_name == worker_filter)
            previous_query = previous_query.filter(Entry.worker_name == worker_filter)
        
        recent_revenue = db.session.query(func.sum(Entry.revenue)).filter(
            Entry.user_id == current_user.id,
            Entry.date >= recent_start,
            Entry.date <= end_date
        )
        previous_revenue = db.session.query(func.sum(Entry.revenue)).filter(
            Entry.user_id == current_user.id,
            Entry.date >= previous_start,
            Entry.date < recent_start
        )
        
        if worker_filter != 'all':
            recent_revenue = recent_revenue.filter(Entry.worker_name == worker_filter)
            previous_revenue = previous_revenue.filter(Entry.worker_name == worker_filter)
        
        recent_rev = recent_revenue.scalar() or 0.0
        previous_rev = previous_revenue.scalar() or 0.0
        
        revenue_change = recent_rev - previous_rev
        revenue_change_percent = (revenue_change / previous_rev * 100) if previous_rev > 0 else 0.0
        revenue_change_percent_abs = abs(revenue_change_percent)
    else:
        revenue_change = 0.0
        revenue_change_percent = 0.0
        revenue_change_percent_abs = 0.0
    
    # Calculate goal progress
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    # Daily revenue (today)
    daily_revenue_query = db.session.query(func.sum(Entry.revenue)).filter(
        Entry.user_id == current_user.id,
        Entry.date == today
    )
    if worker_filter != 'all':
        daily_revenue_query = daily_revenue_query.filter(Entry.worker_name == worker_filter)
    daily_revenue = daily_revenue_query.scalar() or 0.0
    
    # Monthly revenue (current month)
    monthly_revenue_query = db.session.query(func.sum(Entry.revenue)).filter(
        Entry.user_id == current_user.id,
        Entry.date >= month_start,
        Entry.date <= today
    )
    if worker_filter != 'all':
        monthly_revenue_query = monthly_revenue_query.filter(Entry.worker_name == worker_filter)
    monthly_revenue = monthly_revenue_query.scalar() or 0.0
    
    # Calculate monthly take-home amount (current month)
    monthly_take_home_amount = monthly_revenue * (settings.take_home_percent / 100)
    
    # Goal progress calculations (with safe attribute access)
    daily_revenue_goal = getattr(settings, 'daily_revenue_goal', 0.0)
    if daily_revenue_goal is None:
        daily_revenue_goal = 0.0
    
    monthly_revenue_goal = getattr(settings, 'monthly_revenue_goal', 0.0)
    if monthly_revenue_goal is None:
        monthly_revenue_goal = 0.0
    
    profit_quota = getattr(settings, 'profit_quota', 0.0)
    if profit_quota is None:
        profit_quota = 0.0
    
    loss_quota = getattr(settings, 'loss_quota', 0.0)
    if loss_quota is None:
        loss_quota = 0.0
    
    monthly_take_home_goal = getattr(settings, 'monthly_take_home_goal', 0.0)
    if monthly_take_home_goal is None:
        monthly_take_home_goal = 0.0
    
    daily_goal_progress = (daily_revenue / daily_revenue_goal * 100) if daily_revenue_goal > 0 else 0.0
    monthly_goal_progress = (monthly_revenue / monthly_revenue_goal * 100) if monthly_revenue_goal > 0 else 0.0
    monthly_take_home_goal_progress = (monthly_take_home_amount / monthly_take_home_goal * 100) if monthly_take_home_goal > 0 else 0.0
    
    # Calculate days worked this month (needed for both goal and target days calculations)
    days_worked_this_month_query = db.session.query(func.count(func.distinct(Entry.date))).filter(
        Entry.user_id == current_user.id,
        Entry.date >= month_start,
        Entry.date <= today
    )
    if worker_filter != 'all':
        days_worked_this_month_query = days_worked_this_month_query.filter(Entry.worker_name == worker_filter)
    days_worked_this_month = days_worked_this_month_query.scalar() or 0
    
    # Calculate days remaining in month
    last_day_of_month = monthrange(today.year, today.month)[1]
    days_remaining_in_month = last_day_of_month - today.day

    # Nominal workday statistics for the current month
    workday_stats = get_month_workday_stats(today)
    nominal_workdays_total = workday_stats['total']
    nominal_workdays_passed = workday_stats['passed']
    nominal_workdays_remaining = workday_stats['remaining']
    
    # Calculate days needed to achieve monthly take-home goal
    days_needed_for_goal = None
    remaining_take_home_needed = 0.0
    avg_daily_take_home_this_month = 0.0
    
    if monthly_take_home_goal > 0:
        # Calculate remaining take-home needed
        remaining_take_home_needed = monthly_take_home_goal - monthly_take_home_amount
        
        # Calculate average daily take-home for this month
        if days_worked_this_month > 0:
            avg_daily_take_home_this_month = monthly_take_home_amount / days_worked_this_month
        else:
            # Fallback to all-time average if no days worked this month
            avg_daily_take_home_this_month = avg_daily_take_home
        
        # Calculate days needed
        if avg_daily_take_home_this_month > 0:
            days_needed_for_goal = remaining_take_home_needed / avg_daily_take_home_this_month
            # Round up to nearest day
            days_needed_for_goal = max(0, math.ceil(days_needed_for_goal))
        else:
            days_needed_for_goal = None
    
    # Calculate target days status
    target_days_status = None
    target_days_per_month = getattr(settings, 'target_days_per_month', 0)
    if target_days_per_month is None:
        target_days_per_month = 0
    
    if target_days_per_month > 0:
        # Determine status by comparing days needed for goal vs days remaining
        if monthly_take_home_goal > 0 and avg_daily_take_home_this_month > 0 and days_needed_for_goal is not None:
            # Use the calculated days needed for goal
            # Compare days needed vs days remaining using percentages
            if days_remaining_in_month > 0:
                days_needed_percent = (days_needed_for_goal / days_remaining_in_month) * 100
                
                if days_needed_percent <= 70:  # Ahead: need less than 70% of remaining days
                    target_days_status = 'ahead'
                elif days_needed_percent <= 100:  # On Track: need 70-100% of remaining days
                    target_days_status = 'on_track'
                else:  # Behind: need more than 100% of remaining days
                    target_days_status = 'behind_target'
            else:
                # No days remaining in month
                if remaining_take_home_needed <= 0:
                    target_days_status = 'on_target'
                else:
                    target_days_status = 'behind_target'
        elif remaining_take_home_needed <= 0 and monthly_take_home_goal > 0:
            # Goal already achieved
            target_days_status = 'on_target'
        else:
            # No goal set or no average, fall back to simple comparison based on target days
            if days_worked_this_month >= target_days_per_month:
                target_days_status = 'on_target'
            else:
                # Calculate progress through month
                days_elapsed = today.day
                expected_days_worked = (target_days_per_month * days_elapsed) / last_day_of_month
                if days_worked_this_month >= expected_days_worked * 0.9:
                    target_days_status = 'on_track'
                else:
                    target_days_status = 'behind_target'
    
    # P&L status
    profit_quota_met = take_home_amount >= profit_quota if profit_quota > 0 else None
    loss_quota_exceeded = take_home_amount < -loss_quota if loss_quota > 0 else False

    # Required daily take-home target based on remaining workdays
    remaining_take_home_to_goal = max(remaining_take_home_needed, 0.0)
    required_daily_take_home_target = None
    if monthly_take_home_goal > 0 and nominal_workdays_remaining > 0:
        required_daily_take_home_target = remaining_take_home_to_goal / nominal_workdays_remaining
    
    # Get workers for filter dropdown
    workers = Worker.query.filter_by(user_id=current_user.id).order_by(Worker.name).all()
    
    return render_template('dashboard.html',
                         total_revenue=total_revenue,
                         total_hours=total_hours,
                         entry_count=entry_count,
                         avg_daily_revenue=avg_daily_revenue,
                         avg_hours_per_day=avg_hours_per_day,
                         avg_daily_take_home=avg_daily_take_home,
                         avg_hourly_rate=avg_hourly_rate,
                         settings=settings,
                         tax_amount=tax_amount,
                         reinvest_amount=reinvest_amount,
                         take_home_amount=take_home_amount,
                         workers=workers,
                         selected_worker=worker_filter,
                         best_day=best_day,
                         best_day_revenue=best_day_revenue,
                         best_day_hours=best_day_hours,
                         worker_stats=worker_stats,
                         revenue_change=revenue_change,
                         revenue_change_percent=revenue_change_percent,
                         revenue_change_percent_abs=revenue_change_percent_abs,
                         daily_revenue=daily_revenue,
                         monthly_revenue=monthly_revenue,
                         daily_goal_progress=daily_goal_progress,
                         monthly_goal_progress=monthly_goal_progress,
                         monthly_take_home_amount=monthly_take_home_amount,
                         monthly_take_home_goal_progress=monthly_take_home_goal_progress,
                         days_needed_for_goal=days_needed_for_goal,
                         remaining_take_home_needed=remaining_take_home_needed,
                         avg_daily_take_home_this_month=avg_daily_take_home_this_month,
                         days_worked_this_month=days_worked_this_month,
                         days_remaining_in_month=days_remaining_in_month,
                         target_days_per_month=target_days_per_month,
                         target_days_status=target_days_status,
                         profit_quota_met=profit_quota_met,
                         loss_quota_exceeded=loss_quota_exceeded,
                         nominal_workdays_total=nominal_workdays_total,
                         nominal_workdays_passed=nominal_workdays_passed,
                         nominal_workdays_remaining=nominal_workdays_remaining,
                         required_daily_take_home_target=required_daily_take_home_target,
                         remaining_take_home_to_goal=remaining_take_home_to_goal)


@app.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for Chart.js data"""
    period = request.args.get('period', 'daily')
    worker_filter = request.args.get('worker', 'all')
    
    if period == 'daily':
        # Last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=29)
        
        query = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        )
        if worker_filter != 'all':
            query = query.filter(Entry.worker_name == worker_filter)
        entries = query.order_by(Entry.date).all()
        
        # Create date range
        date_range = []
        current = start_date
        while current <= end_date:
            date_range.append(current)
            current += timedelta(days=1)
        
        # Group by date
        revenue_data = {}
        hours_data = {}
        for entry in entries:
            day_str = entry.date.isoformat()
            revenue_data[day_str] = revenue_data.get(day_str, 0) + entry.revenue
            hours_data[day_str] = hours_data.get(day_str, 0) + entry.hours
        
        labels = [d.strftime('%m/%d') for d in date_range]
        revenue_values = [revenue_data.get(d.isoformat(), 0) for d in date_range]
        hours_values = [hours_data.get(d.isoformat(), 0) for d in date_range]
        
    elif period == 'weekly':
        # Last 12 weeks
        end_date = date.today()
        start_date = end_date - timedelta(weeks=11)
        
        query = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        )
        if worker_filter != 'all':
            query = query.filter(Entry.worker_name == worker_filter)
        entries = query.all()
        
        # Group by week
        revenue_data = {}
        hours_data = {}
        for entry in entries:
            # Get ISO week number
            week_key = f"{entry.date.isocalendar()[0]}-W{entry.date.isocalendar()[1]:02d}"
            revenue_data[week_key] = revenue_data.get(week_key, 0) + entry.revenue
            hours_data[week_key] = hours_data.get(week_key, 0) + entry.hours
        
        # Generate labels for last 12 weeks
        labels = []
        revenue_values = []
        hours_values = []
        current = start_date
        for _ in range(12):
            week_key = f"{current.isocalendar()[0]}-W{current.isocalendar()[1]:02d}"
            labels.append(f"Week {current.isocalendar()[1]}")
            revenue_values.append(revenue_data.get(week_key, 0))
            hours_values.append(hours_data.get(week_key, 0))
            current += timedelta(weeks=1)
        
    else:  # monthly
        # Last 12 months
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        query = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        )
        if worker_filter != 'all':
            query = query.filter(Entry.worker_name == worker_filter)
        entries = query.all()
        
        # Group by month
        revenue_data = {}
        hours_data = {}
        for entry in entries:
            month_key = f"{entry.date.year}-{entry.date.month:02d}"
            revenue_data[month_key] = revenue_data.get(month_key, 0) + entry.revenue
            hours_data[month_key] = hours_data.get(month_key, 0) + entry.hours
        
        # Generate labels for last 12 months
        labels = []
        revenue_values = []
        hours_values = []
        current = end_date.replace(day=1)
        for _ in range(12):
            month_key = f"{current.year}-{current.month:02d}"
            labels.append(current.strftime('%b %Y'))
            revenue_values.append(revenue_data.get(month_key, 0))
            hours_values.append(hours_data.get(month_key, 0))
            # Move to previous month
            if current.month == 1:
                current = current.replace(year=current.year - 1, month=12)
            else:
                current = current.replace(month=current.month - 1)
        labels.reverse()
        revenue_values.reverse()
        hours_values.reverse()
    
    # Calculate additional chart metrics
    avg_revenue_per_period = sum(revenue_values) / len([v for v in revenue_values if v > 0]) if any(v > 0 for v in revenue_values) else 0
    max_revenue = max(revenue_values) if revenue_values else 0
    min_revenue = min([v for v in revenue_values if v > 0]) if any(v > 0 for v in revenue_values) else 0
    
    return jsonify({
        'labels': labels,
        'revenue': revenue_values,
        'hours': hours_values,
        'avg_revenue': avg_revenue_per_period,
        'max_revenue': max_revenue,
        'min_revenue': min_revenue
    })


@app.route('/entries')
@login_required
def entries():
    """View all entries with pagination"""
    # Get settings
    settings = Settings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = Settings(
            user_id=current_user.id,
            tax_percent=0.0,
            reinvest_percent=0.0,
            take_home_percent=100.0,
            currency_symbol='$',
            daily_revenue_goal=0.0,
            monthly_revenue_goal=0.0,
            monthly_take_home_goal=0.0,
            target_days_per_month=0,
            profit_quota=0.0,
            loss_quota=0.0
        )
        db.session.add(settings)
        db.session.commit()
    
    # Get worker filter
    worker_filter = request.args.get('worker', 'all')
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(max(per_page, 5), 100)  # Limit between 5 and 100
    
    # Build query
    query = Entry.query.filter_by(user_id=current_user.id)
    if worker_filter != 'all':
        query = query.filter(Entry.worker_name == worker_filter)
    
    # Get paginated entries
    entries = query.order_by(Entry.date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get all workers for filter dropdown
    workers = Worker.query.filter_by(user_id=current_user.id).order_by(Worker.name).all()
    worker_names = [w.name for w in workers]
    
    # Get worker stats for filter dropdown
    worker_stats = []
    if workers:
        for worker in workers:
            worker_entries = Entry.query.filter_by(
                user_id=current_user.id,
                worker_name=worker.name
            ).count()
            if worker_entries > 0:
                worker_stats.append({
                    'name': worker.name,
                    'count': worker_entries
                })
    
    return render_template('entries.html',
                         entries=entries,
                         settings=settings,
                         workers=workers,
                         worker_stats=worker_stats,
                         selected_worker=worker_filter,
                         per_page=per_page)


@app.route('/add_entry', methods=['GET', 'POST'])
@login_required
def add_entry():
    """Add or edit work entry"""
    entry_id = request.args.get('id')
    entry = None
    selected_worker_id = None
    
    if entry_id:
        entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
        if not entry:
            flash('Entry not found.', 'error')
            return redirect(url_for('entries'))
        # Find worker ID for existing entry
        if entry.worker_name:
            worker = Worker.query.filter_by(name=entry.worker_name, user_id=current_user.id).first()
            if worker:
                selected_worker_id = worker.id
    
    # Get workers for dropdown
    workers = Worker.query.filter_by(user_id=current_user.id).order_by(Worker.name).all()
    
    # Get default worker from settings
    settings = Settings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = Settings(
            user_id=current_user.id,
            tax_percent=0.0,
            reinvest_percent=0.0,
            take_home_percent=100.0,
            currency_symbol='$',
            daily_revenue_goal=0.0,
            monthly_revenue_goal=0.0,
            monthly_take_home_goal=0.0,
            target_days_per_month=0,
            profit_quota=0.0,
            loss_quota=0.0
        )
        db.session.add(settings)
        db.session.commit()
    else:
        # Ensure goal fields exist (for existing databases before migration)
        if not hasattr(settings, 'daily_revenue_goal') or settings.daily_revenue_goal is None:
            settings.daily_revenue_goal = 0.0
        if not hasattr(settings, 'monthly_revenue_goal') or settings.monthly_revenue_goal is None:
            settings.monthly_revenue_goal = 0.0
        if not hasattr(settings, 'monthly_take_home_goal') or settings.monthly_take_home_goal is None:
            settings.monthly_take_home_goal = 0.0
        if not hasattr(settings, 'target_days_per_month') or settings.target_days_per_month is None:
            settings.target_days_per_month = 0
        if not hasattr(settings, 'profit_quota') or settings.profit_quota is None:
            settings.profit_quota = 0.0
        if not hasattr(settings, 'loss_quota') or settings.loss_quota is None:
            settings.loss_quota = 0.0
    
    default_worker_id = None
    if settings and settings.default_worker_id:
        default_worker = Worker.query.get(settings.default_worker_id)
        if default_worker:
            default_worker_id = default_worker.id
    
    # Use selected worker ID if editing, otherwise use default
    if not selected_worker_id:
        selected_worker_id = default_worker_id
    
    if request.method == 'POST':
        try:
            entry_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            hours = float(request.form.get('hours', 0))
            revenue = float(request.form.get('revenue', 0))
            worker_id = request.form.get('worker_id', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Get worker name from ID
            worker_name = None
            if worker_id:
                worker = Worker.query.filter_by(id=worker_id, user_id=current_user.id).first()
                if worker:
                    worker_name = worker.name
            
            if hours <= 0:
                flash('Hours must be greater than 0.', 'error')
                return render_template('add_entry.html', entry=entry, workers=workers, default_worker_id=selected_worker_id, settings=settings)
            
            if revenue < 0:
                flash('Revenue cannot be negative.', 'error')
                return render_template('add_entry.html', entry=entry, workers=workers, default_worker_id=selected_worker_id, settings=settings)
            
            if entry:
                # Update existing entry
                entry.date = entry_date
                entry.hours = hours
                entry.revenue = revenue
                entry.worker_name = worker_name
                entry.notes = notes
                entry.updated_at = datetime.utcnow()
                flash('Entry updated successfully.', 'success')
            else:
                # Create new entry
                entry = Entry(
                    date=entry_date,
                    hours=hours,
                    revenue=revenue,
                    worker_name=worker_name,
                    notes=notes,
                    user_id=current_user.id
                )
                db.session.add(entry)
                flash('Entry added successfully.', 'success')
            
            db.session.commit()
            return redirect(url_for('entries'))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving entry: {str(e)}', 'error')
            import traceback
            print(f"Error saving entry: {traceback.format_exc()}")
    
    return render_template('add_entry.html', entry=entry, workers=workers, default_worker_id=selected_worker_id, settings=settings)


@app.route('/delete_entry/<int:entry_id>')
@login_required
def delete_entry(entry_id):
    """Delete work entry"""
    entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash('Entry deleted successfully.', 'success')
    else:
        flash('Entry not found.', 'error')
    # Redirect back to the page that called this (entries or dashboard)
    referrer = request.referrer
    if referrer and 'entries' in referrer:
        return redirect(url_for('entries'))
    return redirect(url_for('dashboard'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Configure percentage settings and workers"""
    settings_obj = Settings.query.filter_by(user_id=current_user.id).first()
    
    if not settings_obj:
        settings_obj = Settings(
            user_id=current_user.id,
            tax_percent=0.0,
            reinvest_percent=0.0,
            take_home_percent=100.0,
            currency_symbol='$',
            daily_revenue_goal=0.0,
            monthly_revenue_goal=0.0,
            monthly_take_home_goal=0.0,
            profit_quota=0.0,
            loss_quota=0.0
        )
        db.session.add(settings_obj)
        db.session.commit()
    else:
        # Ensure goal fields exist (for existing databases before migration)
        if not hasattr(settings_obj, 'daily_revenue_goal') or settings_obj.daily_revenue_goal is None:
            settings_obj.daily_revenue_goal = 0.0
        if not hasattr(settings_obj, 'monthly_revenue_goal') or settings_obj.monthly_revenue_goal is None:
            settings_obj.monthly_revenue_goal = 0.0
        if not hasattr(settings_obj, 'monthly_take_home_goal') or settings_obj.monthly_take_home_goal is None:
            settings_obj.monthly_take_home_goal = 0.0
        if not hasattr(settings_obj, 'target_days_per_month') or settings_obj.target_days_per_month is None:
            settings_obj.target_days_per_month = 0
        if not hasattr(settings_obj, 'profit_quota') or settings_obj.profit_quota is None:
            settings_obj.profit_quota = 0.0
        if not hasattr(settings_obj, 'loss_quota') or settings_obj.loss_quota is None:
            settings_obj.loss_quota = 0.0
    
    # Get workers
    workers = Worker.query.filter_by(user_id=current_user.id).order_by(Worker.name).all()
    
    if request.method == 'POST':
        # Handle percentage settings
        if 'tax_percent' in request.form:
            try:
                tax_percent = float(request.form.get('tax_percent', 0))
                reinvest_percent = float(request.form.get('reinvest_percent', 0))
                take_home_percent = float(request.form.get('take_home_percent', 0))
                
                total = tax_percent + reinvest_percent + take_home_percent
                if abs(total - 100.0) > 0.01:  # Allow small floating point differences
                    flash(f'Percentages must sum to 100%. Current sum: {total:.2f}%', 'error')
                    return render_template('settings.html', settings=settings_obj, workers=workers)
                
                settings_obj.tax_percent = tax_percent
                settings_obj.reinvest_percent = reinvest_percent
                settings_obj.take_home_percent = take_home_percent
                settings_obj.updated_at = datetime.utcnow()
                db.session.commit()
                flash('Settings updated successfully.', 'success')
                return redirect(url_for('settings'))
                
            except ValueError:
                flash('Invalid input. Please enter valid numbers.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving settings: {str(e)}', 'error')
        
        # Handle adding worker
        elif 'add_worker' in request.form:
            worker_name = request.form.get('worker_name', '').strip()
            if worker_name:
                # Check if worker already exists
                existing = Worker.query.filter_by(name=worker_name, user_id=current_user.id).first()
                if existing:
                    flash(f'Worker "{worker_name}" already exists.', 'error')
                else:
                    worker = Worker(name=worker_name, user_id=current_user.id)
                    db.session.add(worker)
                    db.session.commit()
                    flash(f'Worker "{worker_name}" added successfully.', 'success')
                    return redirect(url_for('settings'))
            else:
                flash('Worker name cannot be empty.', 'error')
        
        # Handle setting default worker
        elif 'set_default_worker' in request.form:
            worker_id = request.form.get('default_worker_id', '').strip()
            if worker_id:
                worker = Worker.query.filter_by(id=worker_id, user_id=current_user.id).first()
                if worker:
                    settings_obj.default_worker_id = worker.id
                    settings_obj.updated_at = datetime.utcnow()
                    db.session.commit()
                    flash(f'Default worker set to "{worker.name}".', 'success')
                    return redirect(url_for('settings'))
            else:
                # Clear default worker
                settings_obj.default_worker_id = None
                settings_obj.updated_at = datetime.utcnow()
                db.session.commit()
                flash('Default worker cleared.', 'success')
                return redirect(url_for('settings'))
        
        # Handle currency symbol change
        elif 'set_currency' in request.form:
            currency_symbol = request.form.get('currency_symbol', '$').strip()
            if currency_symbol in ['$', '£']:
                settings_obj.currency_symbol = currency_symbol
                settings_obj.updated_at = datetime.utcnow()
                db.session.commit()
                flash(f'Currency symbol set to {currency_symbol}.', 'success')
                return redirect(url_for('settings'))
            else:
                flash('Invalid currency symbol. Please select $ or £.', 'error')
        
        # Handle goals and quotas
        elif 'set_goals' in request.form:
            print(f"DEBUG: set_goals handler called. Form data: {dict(request.form)}")
            try:
                # Helper function to safely convert form values to float
                def safe_float(value, default=0.0):
                    if not value:
                        return default
                    if isinstance(value, str) and value.strip() == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                # Get form values
                daily_revenue_goal = safe_float(request.form.get('daily_revenue_goal', ''))
                monthly_revenue_goal = safe_float(request.form.get('monthly_revenue_goal', ''))
                monthly_take_home_goal = safe_float(request.form.get('monthly_take_home_goal', ''))
                target_days_per_month = int(safe_float(request.form.get('target_days_per_month', '')))
                profit_quota = safe_float(request.form.get('profit_quota', ''))
                loss_quota = safe_float(request.form.get('loss_quota', ''))
                
                # Update settings
                settings_obj.daily_revenue_goal = daily_revenue_goal
                settings_obj.monthly_revenue_goal = monthly_revenue_goal
                settings_obj.monthly_take_home_goal = monthly_take_home_goal
                settings_obj.target_days_per_month = target_days_per_month
                settings_obj.profit_quota = profit_quota
                settings_obj.loss_quota = loss_quota
                settings_obj.updated_at = datetime.utcnow()
                
                # Commit changes
                db.session.commit()
                flash('Goals and quotas updated successfully.', 'success')
                return redirect(url_for('settings'))
            except ValueError as e:
                flash(f'Invalid input for goals. Please enter valid numbers. Error: {str(e)}', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving goals: {str(e)}', 'error')
                import traceback
                print(f"Error saving goals: {traceback.format_exc()}")
    
    return render_template('settings.html', settings=settings_obj, workers=workers)


@app.route('/delete_worker/<int:worker_id>')
@login_required
def delete_worker(worker_id):
    """Delete a worker"""
    worker = Worker.query.filter_by(id=worker_id, user_id=current_user.id).first()
    if worker:
        # Check if it's the default worker
        settings = Settings.query.filter_by(user_id=current_user.id).first()
        if settings and settings.default_worker_id == worker.id:
            settings.default_worker_id = None
        
        # Delete entries associated with this worker
        Entry.query.filter_by(worker_name=worker.name, user_id=current_user.id).delete()
        
        db.session.delete(worker)
        db.session.commit()
        flash(f'Worker "{worker.name}" deleted successfully.', 'success')
    else:
        flash('Worker not found.', 'error')
    return redirect(url_for('settings'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)

