import sys
import sklearn._loss
def dummy_unpickle(*args, **kwargs):
    return None

# Patch for loading older scikit-learn XGBoost/HistGradientBoosting models
sys.modules['_loss'] = sklearn._loss
sklearn._loss.__pyx_unpickle_CyHalfMultinomialLoss = dummy_unpickle
sklearn._loss.__pyx_unpickle_HalfMultinomialLoss = dummy_unpickle
sklearn._loss.CyHalfMultinomialLoss = getattr(sklearn._loss, 'HalfMultinomialLoss', None)
sklearn._loss.CyHalfBinomialLoss = getattr(sklearn._loss, 'HalfBinomialLoss', None)

from flask import Flask, jsonify
from flask_cors import CORS
from routes.prediction import prediction_bp
from routes.signals import signals_bp

app = Flask(__name__)
# Allow CORS for Vite dev server and default ports
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(prediction_bp, url_prefix='/api')
app.register_blueprint(signals_bp, url_prefix='/api/signals')

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "message": "CryptoBuddy ML Backend API is running.",
        "endpoints": [
            "POST /api/predict",
            "GET /api/signals/recent",
            "GET /api/signals/summary",
            "GET /api/health"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "CryptoBuddy ML Backend"})

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
