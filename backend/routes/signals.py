from flask import Blueprint, jsonify, request
import json
import os

signals_bp = Blueprint('signals', __name__)

LOG_FILE = "models/reports/signal_log.jsonl"
SUMMARY_FILE = "models/reports/signal_summary.json"

@signals_bp.route('/recent', methods=['GET'])
def get_recent_signals():
    symbol = request.args.get('symbol')
    limit = request.args.get('limit', 10, type=int)
    
    signals = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
                # Read from newest to oldest
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if symbol and entry.get('symbol') != symbol:
                        continue
                    signals.append(entry)
                    if len(signals) >= limit:
                        break
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to read logs: {e}"}), 500
            
    return jsonify(signals)

@signals_bp.route('/summary', methods=['GET'])
def get_signals_summary():
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r") as f:
                data = json.load(f)
                return jsonify(data)
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to read summary: {e}"}), 500
    
    return jsonify({"success": False, "error": "Summary not found"}), 404
