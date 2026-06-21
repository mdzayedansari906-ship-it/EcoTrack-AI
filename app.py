from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime
from datetime import timedelta
import db
import calculator
import gemini_service

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ecotrack_secret_key_1293810238")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize database on start
with app.app_context():
    db.init_db()

def get_current_user_id():
    return session.get('user_id')

def check_and_unlock_achievements(user_id, conn):
    """
    Check if user has met requirements for any locked achievements,
    unlocks them, and returns the unlocked achievements list.
    """
    cursor = conn.cursor()
    
    # Get all achievements the user has NOT unlocked yet
    cursor.execute('''
    SELECT * FROM achievements WHERE id NOT IN (
        SELECT achievement_id FROM user_achievements WHERE user_id = ?
    )
    ''', (user_id,))
    locked_achievements = cursor.fetchall()
    
    unlocked = []
    
    for ach in locked_achievements:
        key = ach['key']
        target_type = ach['target_type']
        target_val = ach['target_value']
        should_unlock = False
        
        if key == 'first_log':
            # Count footprint entries
            cursor.execute('SELECT COUNT(*) FROM footprint_logs WHERE user_id = ?', (user_id,))
            count = cursor.fetchone()[0]
            if count >= target_val:
                should_unlock = True
                
        elif key == 'eco_traveler':
            # Look for active/public transit logs
            cursor.execute('''
            SELECT COUNT(*) FROM footprint_logs 
            WHERE user_id = ? AND transport_type IN ('active', 'public_transit') AND transport_miles > 0
            ''', (user_id,))
            count = cursor.fetchone()[0]
            if count >= target_val:
                should_unlock = True
                
        elif key == 'plant_powered':
            # Look for vegetarian/vegan logs
            cursor.execute('''
            SELECT COUNT(*) FROM footprint_logs 
            WHERE user_id = ? AND diet_type IN ('vegan', 'vegetarian')
            ''', (user_id,))
            count = cursor.fetchone()[0]
            if count >= target_val:
                should_unlock = True
                
        elif key == 'carbon_saver':
            # Keep carbon below 10 kg CO2
            cursor.execute('''
            SELECT COUNT(*) FROM footprint_logs 
            WHERE user_id = ? AND carbon_emissions > 0 AND carbon_emissions < 10.0
            ''', (user_id,))
            count = cursor.fetchone()[0]
            if count >= target_val:
                should_unlock = True
                
        elif key == 'streak_3':
            # Check 3 consecutive days
            cursor.execute('SELECT DISTINCT date FROM footprint_logs WHERE user_id = ? ORDER BY date', (user_id,))
            date_rows = cursor.fetchall()
            dates = []
            for row in date_rows:
                try:
                    dates.append(datetime.datetime.strptime(row['date'], '%Y-%m-%d').date())
                except ValueError:
                    pass
            
            # Check for streak
            streak_len = 0
            max_streak = 0
            if len(dates) >= 3:
                dates = sorted(list(set(dates)))
                streak_len = 1
                for i in range(1, len(dates)):
                    if (dates[i] - dates[i-1]).days == 1:
                        streak_len += 1
                    else:
                        if streak_len > max_streak:
                            max_streak = streak_len
                        streak_len = 1
                if streak_len > max_streak:
                    max_streak = streak_len
                
                if max_streak >= target_val:
                    should_unlock = True
                    
        elif key == 'task_finisher':
            # Check completed recommendations count
            cursor.execute('SELECT COUNT(*) FROM recommendations WHERE user_id = ? AND completed = 1', (user_id,))
            count = cursor.fetchone()[0]
            if count >= target_val:
                should_unlock = True

        if should_unlock:
            cursor.execute('''
            INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
            VALUES (?, ?)
            ''', (user_id, ach['id']))
            unlocked.append({
                'key': key,
                'name': ach['name'],
                'description': ach['description'],
                'badge_icon': ach['badge_icon']
            })
            
    if unlocked:
        conn.commit()
        
    return unlocked

# Frontend Routes
@app.route('/')
def index():
    return render_template('index.html')

# Authentication APIs
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required.'}), 400
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Username or email already exists.'}), 400
        
    # Create user
    pw_hash = generate_password_hash(password)
    try:
        cursor.execute('''
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
        ''', (username, email, pw_hash))
        conn.commit()
        
        # Log them in automatically
        cursor.execute('SELECT id, username FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        conn.close()
        return jsonify({'message': 'Registration successful.', 'user': {'username': user['username']}})
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Database registration failed: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'message': 'Login successful.', 'user': {'username': user['username']}})
    else:
        return jsonify({'error': 'Invalid username or password.'}), 401

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully.'})

@app.route('/api/auth/me', methods=['GET', 'POST'])
def me():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        daily_goal = data.get('daily_goal')
        password = data.get('password', '')
        
        if not email:
            conn.close()
            return jsonify({'error': 'Email is required.'}), 400
            
        try:
            # Check unique email
            cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, uid))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Email is already taken.'}), 400
                
            if password:
                pw_hash = generate_password_hash(password)
                cursor.execute('''
                UPDATE users SET email = ?, daily_goal = ?, password_hash = ? WHERE id = ?
                ''', (email, float(daily_goal or 20.0), pw_hash, uid))
            else:
                cursor.execute('''
                UPDATE users SET email = ?, daily_goal = ? WHERE id = ?
                ''', (email, float(daily_goal or 20.0), uid))
                
            conn.commit()
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500
            
    cursor.execute('SELECT username, email, daily_goal FROM users WHERE id = ?', (uid,))
    user = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'username': user['username'],
        'email': user['email'],
        'daily_goal': user['daily_goal']
    })

# Footprint APIs
@app.route('/api/footprint', methods=['GET', 'POST'])
def footprint():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json() or {}
        date_str = data.get('date') or datetime.date.today().strftime('%Y-%m-%d')
        transport_miles = float(data.get('transport_miles', 0))
        transport_type = data.get('transport_type', 'active')
        electricity_kwh = float(data.get('electricity_kwh', 0))
        diet_type = data.get('diet_type', 'average')
        
        # Calculate carbon emissions
        res = calculator.calculate_footprint(transport_miles, transport_type, electricity_kwh, diet_type)
        carbon_emissions = res['total']
        
        try:
            cursor.execute('''
            INSERT INTO footprint_logs (user_id, date, transport_miles, transport_type, electricity_kwh, diet_type, carbon_emissions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                transport_miles = excluded.transport_miles,
                transport_type = excluded.transport_type,
                electricity_kwh = excluded.electricity_kwh,
                diet_type = excluded.diet_type,
                carbon_emissions = excluded.carbon_emissions
            ''', (uid, date_str, transport_miles, transport_type, electricity_kwh, diet_type, carbon_emissions))
            conn.commit()
            
            # Check achievements
            unlocked_badges = check_and_unlock_achievements(uid, conn)
            
            conn.close()
            return jsonify({
                'message': 'Footprint logged successfully.',
                'emissions': res,
                'newly_unlocked': unlocked_badges
            })
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Failed to save footprint: {str(e)}'}), 500
            
    # GET method - return sorted list of entries
    cursor.execute('''
    SELECT date, transport_miles, transport_type, electricity_kwh, diet_type, carbon_emissions 
    FROM footprint_logs WHERE user_id = ? ORDER BY date DESC LIMIT 30
    ''', (uid,))
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            'date': r['date'],
            'transport_miles': r['transport_miles'],
            'transport_type': r['transport_type'],
            'electricity_kwh': r['electricity_kwh'],
            'diet_type': r['diet_type'],
            'carbon_emissions': r['carbon_emissions']
        })
        
    return jsonify(logs)

# Dashboard Summary Data
@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Get user details
    cursor.execute('SELECT daily_goal FROM users WHERE id = ?', (uid,))
    user_row = cursor.fetchone()
    daily_goal = user_row['daily_goal'] if user_row else 20.0
    
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    # 1. Today's emissions
    cursor.execute('SELECT carbon_emissions FROM footprint_logs WHERE user_id = ? AND date = ?', (uid, today_str))
    today_row = cursor.fetchone()
    today_emissions = today_row['carbon_emissions'] if today_row else 0.0
    
    # 2. Weekly emissions (sum of emissions in last 7 days)
    seven_days_ago = (datetime.date.today() - timedelta(days=6)).strftime('%Y-%m-%d')
    cursor.execute('''
    SELECT SUM(carbon_emissions) as total_weekly FROM footprint_logs 
    WHERE user_id = ? AND date >= ? AND date <= ?
    ''', (uid, seven_days_ago, today_str))
    weekly_row = cursor.fetchone()
    weekly_emissions = weekly_row['total_weekly'] if weekly_row['total_weekly'] is not None else 0.0
    
    # 3. Monthly emissions (sum of emissions in last 30 days)
    thirty_days_ago = (datetime.date.today() - timedelta(days=29)).strftime('%Y-%m-%d')
    cursor.execute('''
    SELECT SUM(carbon_emissions) as total_monthly FROM footprint_logs 
    WHERE user_id = ? AND date >= ? AND date <= ?
    ''', (uid, thirty_days_ago, today_str))
    monthly_row = cursor.fetchone()
    monthly_emissions = monthly_row['total_monthly'] if monthly_row['total_monthly'] is not None else 0.0
    
    # 4. Breakdown over the last 30 days
    cursor.execute('''
    SELECT transport_miles, transport_type, electricity_kwh, diet_type FROM footprint_logs 
    WHERE user_id = ? AND date >= ? AND date <= ?
    ''', (uid, thirty_days_ago, today_str))
    logs_30 = cursor.fetchall()
    
    t_sum = 0.0
    e_sum = 0.0
    d_sum = 0.0
    for l in logs_30:
        res = calculator.calculate_footprint(l['transport_miles'], l['transport_type'], l['electricity_kwh'], l['diet_type'])
        t_sum += res['transport']
        e_sum += res['electricity']
        d_sum += res['diet']
        
    breakdown = {
        'transportation': round(t_sum, 2),
        'electricity': round(e_sum, 2),
        'diet': round(d_sum, 2)
    }
    
    # 5. History over the last 7 days for plotting (ordered chronologically)
    history = []
    for i in range(6, -1, -1):
        d = (datetime.date.today() - timedelta(days=i))
        d_str = d.strftime('%Y-%m-%d')
        cursor.execute('SELECT carbon_emissions FROM footprint_logs WHERE user_id = ? AND date = ?', (uid, d_str))
        hist_row = cursor.fetchone()
        history.append({
            'label': d.strftime('%b %d'),
            'date': d_str,
            'emissions': hist_row['carbon_emissions'] if hist_row else 0.0
        })
        
    # 6. Recent Logs (last 5 entries)
    cursor.execute('''
    SELECT date, carbon_emissions FROM footprint_logs 
    WHERE user_id = ? ORDER BY date DESC LIMIT 5
    ''', (uid,))
    recent_rows = cursor.fetchall()
    recent = [{'date': r['date'], 'emissions': r['carbon_emissions']} for r in recent_rows]
    
    conn.close()
    
    return jsonify({
        'today': today_emissions,
        'weekly': weekly_emissions,
        'monthly': monthly_emissions,
        'daily_goal': daily_goal,
        'breakdown': breakdown,
        'history': history,
        'recent': recent
    })

# Recommendations APIs
@app.route('/api/recommendations', methods=['GET'])
def recommendations():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Get active recommendations
    cursor.execute('''
    SELECT id, category, suggestion, completed FROM recommendations 
    WHERE user_id = ? AND completed = 0 ORDER BY id DESC
    ''', (uid,))
    recs = cursor.fetchall()
    
    # If no active recommendations, generate new ones automatically
    if not recs:
        # Collect user averages for input stats
        thirty_days_ago = (datetime.date.today() - timedelta(days=29)).strftime('%Y-%m-%d')
        cursor.execute('''
        SELECT transport_miles, transport_type, electricity_kwh, diet_type, carbon_emissions 
        FROM footprint_logs WHERE user_id = ? AND date >= ?
        ''', (uid, thirty_days_ago))
        logs = cursor.fetchall()
        
        avg_transport = 0.0
        avg_elec = 0.0
        trans_types = {}
        diet_types = {}
        avg_emissions = 0.0
        
        if logs:
            for l in logs:
                avg_transport += l['transport_miles']
                avg_elec += l['electricity_kwh']
                avg_emissions += l['carbon_emissions']
                
                tt = l['transport_type']
                trans_types[tt] = trans_types.get(tt, 0) + 1
                
                dt = l['diet_type']
                diet_types[dt] = diet_types.get(dt, 0) + 1
                
            n = len(logs)
            avg_transport /= n
            avg_elec /= n
            avg_emissions /= n
            
            pred_trans = max(trans_types, key=trans_types.get) if trans_types else 'active'
            pred_diet = max(diet_types, key=diet_types.get) if diet_types else 'average'
        else:
            pred_trans = 'active'
            pred_diet = 'average'
            
        cursor.execute('SELECT daily_goal FROM users WHERE id = ?', (uid,))
        user_row = cursor.fetchone()
        daily_goal = user_row['daily_goal'] if user_row else 20.0
        
        stats = {
            'avg_transport_miles': avg_transport,
            'avg_electricity_kwh': avg_elec,
            'predominant_transport_type': pred_trans,
            'predominant_diet_type': pred_diet,
            'avg_emissions': avg_emissions,
            'daily_goal': daily_goal
        }
        
        new_recs = gemini_service.generate_recommendations(stats)
        for r in new_recs:
            cursor.execute('''
            INSERT INTO recommendations (user_id, category, suggestion, completed)
            VALUES (?, ?, ?, 0)
            ''', (uid, r['category'], r['suggestion']))
        conn.commit()
        
        cursor.execute('''
        SELECT id, category, suggestion, completed FROM recommendations 
        WHERE user_id = ? AND completed = 0 ORDER BY id DESC
        ''', (uid,))
        recs = cursor.fetchall()
        
    conn.close()
    
    return jsonify([{
        'id': r['id'],
        'category': r['category'],
        'suggestion': r['suggestion'],
        'completed': r['completed']
    } for r in recs])

@app.route('/api/recommendations/generate', methods=['POST'])
def force_generate():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Delete current active incomplete suggestions to avoid clutter
    cursor.execute('DELETE FROM recommendations WHERE user_id = ? AND completed = 0', (uid,))
    
    # Same stats extraction logic
    thirty_days_ago = (datetime.date.today() - timedelta(days=29)).strftime('%Y-%m-%d')
    cursor.execute('''
    SELECT transport_miles, transport_type, electricity_kwh, diet_type, carbon_emissions 
    FROM footprint_logs WHERE user_id = ? AND date >= ?
    ''', (uid, thirty_days_ago))
    logs = cursor.fetchall()
    
    avg_transport = 0.0
    avg_elec = 0.0
    trans_types = {}
    diet_types = {}
    avg_emissions = 0.0
    
    if logs:
        for l in logs:
            avg_transport += l['transport_miles']
            avg_elec += l['electricity_kwh']
            avg_emissions += l['carbon_emissions']
            
            tt = l['transport_type']
            trans_types[tt] = trans_types.get(tt, 0) + 1
            
            dt = l['diet_type']
            diet_types[dt] = diet_types.get(dt, 0) + 1
            
        n = len(logs)
        avg_transport /= n
        avg_elec /= n
        avg_emissions /= n
        
        pred_trans = max(trans_types, key=trans_types.get) if trans_types else 'active'
        pred_diet = max(diet_types, key=diet_types.get) if diet_types else 'average'
    else:
        pred_trans = 'active'
        pred_diet = 'average'
        
    cursor.execute('SELECT daily_goal FROM users WHERE id = ?', (uid,))
    user_row = cursor.fetchone()
    daily_goal = user_row['daily_goal'] if user_row else 20.0
    
    stats = {
        'avg_transport_miles': avg_transport,
        'avg_electricity_kwh': avg_elec,
        'predominant_transport_type': pred_trans,
        'predominant_diet_type': pred_diet,
        'avg_emissions': avg_emissions,
        'daily_goal': daily_goal
    }
    
    try:
        new_recs = gemini_service.generate_recommendations(stats)
        for r in new_recs:
            cursor.execute('''
            INSERT INTO recommendations (user_id, category, suggestion, completed)
            VALUES (?, ?, ?, 0)
            ''', (uid, r['category'], r['suggestion']))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to generate recommendations: {str(e)}'}), 500
        
    cursor.execute('''
    SELECT id, category, suggestion, completed FROM recommendations 
    WHERE user_id = ? AND completed = 0 ORDER BY id DESC
    ''', (uid,))
    recs = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': r['id'],
        'category': r['category'],
        'suggestion': r['suggestion'],
        'completed': r['completed']
    } for r in recs])

@app.route('/api/recommendations/<int:rec_id>/complete', methods=['PUT', 'POST'])
def complete_recommendation(rec_id):
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute('SELECT id FROM recommendations WHERE id = ? AND user_id = ?', (rec_id, uid))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Recommendation not found.'}), 404
        
    try:
        cursor.execute('UPDATE recommendations SET completed = 1 WHERE id = ?', (rec_id,))
        conn.commit()
        
        # Check achievements
        unlocked_badges = check_and_unlock_achievements(uid, conn)
        
        conn.close()
        return jsonify({
            'message': 'Recommendation marked as completed.',
            'newly_unlocked': unlocked_badges
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to complete recommendation: {str(e)}'}), 500

# Achievements API
@app.route('/api/achievements', methods=['GET'])
def get_achievements():
    uid = get_current_user_id()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all achievements
    cursor.execute('SELECT id, key, name, description, badge_icon FROM achievements')
    all_ach = cursor.fetchall()
    
    # Fetch unlocked achievements
    cursor.execute('SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id = ?', (uid,))
    unlocked_rows = cursor.fetchall()
    unlocked_map = {row['achievement_id']: row['unlocked_at'] for row in unlocked_rows}
    
    conn.close()
    
    list_ach = []
    for a in all_ach:
        aid = a['id']
        is_unlocked = aid in unlocked_map
        list_ach.append({
            'id': aid,
            'key': a['key'],
            'name': a['name'],
            'description': a['description'],
            'badge_icon': a['badge_icon'],
            'unlocked': is_unlocked,
            'unlocked_at': unlocked_map[aid] if is_unlocked else None
        })
        
    return jsonify(list_ach)

if __name__ == '__main__':
    # Run server locally on port 5001
    app.run(host='0.0.0.0', port=5001, debug=True)
