from flask import Flask, jsonify, render_template
import db_logger

app = Flask(__name__)


def transform_to_hourly(presses):
    """Convert button press records into hourly counts for the dashboard."""
    hourly_counts = [0] * 24
    for p in presses:
        hour = p.get('hour')
        if isinstance(hour, int) and 0 <= hour < 24:
            hourly_counts[hour] += 1
    return [{'hour': idx, 'count': count} for idx, count in enumerate(hourly_counts)]


@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    
    presses = db_logger.fetch_all_button_presses()
    phases = db_logger.fetch_all_phases()
    
    
    return jsonify({
        "total_presses": len(presses),
        "latest_state": phases[-1]['phase'] if phases else "UNKNOWN",
        "hourly_data": transform_to_hourly(presses) 
    })

@app.route('/api/realtime_stats')
def realtime_stats():
    
    presses = db_logger.fetch_all_button_presses()
    latest = db_logger.fetch_latest_phase()
    
    
    return jsonify({
        "current_phase": latest.get('phase', 'UNKNOWN'),
        "total_pedestrians": len(presses),
        "recent_activity": [p['timestamp'] for p in presses[-10:]]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)