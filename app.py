from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from models import db, User, Entry, Settings
from config import get_config
import os
import json

app = Flask(__name__)
app.config.from_object(get_config())

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))


def init_db():
    """Initialize database and create default user if needed"""
    with app.app_context():
        db.create_all()
        
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
                take_home_percent=55.0
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
            take_home_percent=100.0
        )
        db.session.add(settings)
        db.session.commit()
    
    # Get all entries for current user
    entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.date.desc()).limit(10).all()
    
    # Calculate totals
    total_revenue = db.session.query(func.sum(Entry.revenue)).filter_by(user_id=current_user.id).scalar() or 0.0
    total_hours = db.session.query(func.sum(Entry.hours)).filter_by(user_id=current_user.id).scalar() or 0.0
    entry_count = Entry.query.filter_by(user_id=current_user.id).count()
    
    # Calculate averages
    avg_daily_revenue = total_revenue / entry_count if entry_count > 0 else 0.0
    avg_hours_per_day = total_hours / entry_count if entry_count > 0 else 0.0
    
    # Calculate amounts based on percentages
    tax_amount = total_revenue * (settings.tax_percent / 100)
    reinvest_amount = total_revenue * (settings.reinvest_percent / 100)
    take_home_amount = total_revenue * (settings.take_home_percent / 100)
    
    return render_template('dashboard.html',
                         entries=entries,
                         total_revenue=total_revenue,
                         total_hours=total_hours,
                         entry_count=entry_count,
                         avg_daily_revenue=avg_daily_revenue,
                         avg_hours_per_day=avg_hours_per_day,
                         settings=settings,
                         tax_amount=tax_amount,
                         reinvest_amount=reinvest_amount,
                         take_home_amount=take_home_amount)


@app.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for Chart.js data"""
    period = request.args.get('period', 'daily')
    
    if period == 'daily':
        # Last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=29)
        
        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        ).order_by(Entry.date).all()
        
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
        
        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        ).all()
        
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
        
        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.date >= start_date,
            Entry.date <= end_date
        ).all()
        
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
    
    return jsonify({
        'labels': labels,
        'revenue': revenue_values,
        'hours': hours_values
    })


@app.route('/add_entry', methods=['GET', 'POST'])
@login_required
def add_entry():
    """Add or edit work entry"""
    entry_id = request.args.get('id')
    entry = None
    
    if entry_id:
        entry = Entry.query.filter_by(id=entry_id, user_id=current_user.id).first()
        if not entry:
            flash('Entry not found.', 'error')
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            entry_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            hours = float(request.form.get('hours', 0))
            revenue = float(request.form.get('revenue', 0))
            worker_name = request.form.get('worker_name', '').strip()
            notes = request.form.get('notes', '').strip()
            
            if hours <= 0:
                flash('Hours must be greater than 0.', 'error')
                return render_template('add_entry.html', entry=entry)
            
            if revenue < 0:
                flash('Revenue cannot be negative.', 'error')
                return render_template('add_entry.html', entry=entry)
            
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
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving entry: {str(e)}', 'error')
    
    return render_template('add_entry.html', entry=entry)


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
    return redirect(url_for('dashboard'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Configure percentage settings"""
    settings_obj = Settings.query.filter_by(user_id=current_user.id).first()
    
    if not settings_obj:
        settings_obj = Settings(
            user_id=current_user.id,
            tax_percent=0.0,
            reinvest_percent=0.0,
            take_home_percent=100.0
        )
        db.session.add(settings_obj)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            tax_percent = float(request.form.get('tax_percent', 0))
            reinvest_percent = float(request.form.get('reinvest_percent', 0))
            take_home_percent = float(request.form.get('take_home_percent', 0))
            
            total = tax_percent + reinvest_percent + take_home_percent
            if abs(total - 100.0) > 0.01:  # Allow small floating point differences
                flash(f'Percentages must sum to 100%. Current sum: {total:.2f}%', 'error')
                return render_template('settings.html', settings=settings_obj)
            
            settings_obj.tax_percent = tax_percent
            settings_obj.reinvest_percent = reinvest_percent
            settings_obj.take_home_percent = take_home_percent
            settings_obj.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Settings updated successfully.', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError:
            flash('Invalid input. Please enter valid numbers.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving settings: {str(e)}', 'error')
    
    return render_template('settings.html', settings=settings_obj)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)

