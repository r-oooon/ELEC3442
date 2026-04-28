from flask import Flask, jsonify, render_template, current_app
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

# @app.route('/api/stats')
# def get_stats():
#
#     presses = db_logger.fetch_all_button_presses()
#     phases = db_logger.fetch_all_phases()
#
#
#     return jsonify({
#         "total_presses": len(presses),
#         "latest_state": phases[-1]['phase'] if phases else "UNKNOWN",
#         "hourly_data": transform_to_hourly(presses)
#     })

@app.route('/api/stats')
def get_stats():
    # Fetch data from SQLite
    presses = db_logger.fetch_all_button_presses()
    phases = db_logger.fetch_all_phases()

    return jsonify({
        "total_presses": len(presses),
        "latest_state": phases[-1]['phase'] if phases else "UNKNOWN",
        "hourly_data": transform_to_hourly(presses),  # Legacy support
        # NEW: Provide raw data for client-side processing
        "raw_presses": presses,
        "raw_phases": phases
    })


@app.route('/api/realtime_stats')
def realtime_stats():
    try:
        shared_state = current_app.config.get('LIVE_STATE')
        current_phase = "UNKNOWN"

        if shared_state:
            with shared_state['lock']:
                current_phase = shared_state.get('current_state', 'UNKNOWN')
        else:
            # If main.py hasn't shared the state yet, try the DB
            latest = db_logger.fetch_latest_phase()
            current_phase = latest.get('phase', 'UNKNOWN') if latest else "INITIALIZING"

        presses = db_logger.fetch_all_button_presses()

        return jsonify({
            "current_phase": current_phase,
            "total_pedestrians": len(presses),
            "recent_activity": [p['timestamp'] for p in presses[-10:]]
        })
    except Exception as e:
        # This will print the exact error to your terminal if the API fails
        print(f"API Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.after_request
def add_header(response):
    """Disable browser caching for all API responses."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)