import logging
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from auth.auth import auth_bp
from models.models import db
from salesforce_api.assets import assets_bp
from salesforce_api.campaigns import campaigns_bp
from salesforce_api.contacts import contacts_bp
from salesforce_api.data_events import data_events_bp
from salesforce_api.email_definitions import email_definitions_bp

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Config DB
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'marketing-cloud-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///marketing_cloud.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'jwt-secret-key-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)

app.config['RATELIMIT_STORAGE_URL'] = os.environ.get('REDIS_URL', 'memory://')

db.init_app(app)

CORS(app, origins=['*'])

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri=app.config['RATELIMIT_STORAGE_URL']
)


app.register_blueprint(auth_bp, url_prefix='/v1/auth')
app.register_blueprint(contacts_bp, url_prefix='/contacts/v1')
app.register_blueprint(campaigns_bp, url_prefix='/campaigns/v1')
app.register_blueprint(email_definitions_bp, url_prefix='/email/v1')
app.register_blueprint(data_events_bp, url_prefix='/data/v1')
app.register_blueprint(assets_bp, url_prefix='/assets/v1')


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found',
                    'message': 'The requested endpoint does not exist',
                    'errorcode': 404}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error',
                    'message': 'An unexpected error occurred',
                    'errorcode': 500}), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded',
                    'message': f'Rate limit exceeded: {e.description}',
                    'errorcode': 429}), 429


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                    'service': 'Marketing Cloud API Clone'})


@app.route('/v1', methods=['GET'])
@limiter.limit("60 per minute")
def api_info():
    return jsonify({
        'name': 'Marketing Cloud API Clone',
        'version': '1.0.0',
        'description': 'Salesforce Marketing Cloud API simulation',
        'endpoints': {
            'authentication': '/v1/auth',
            'contacts': '/contacts/v1',
            'campaigns': '/campaigns/v1',
            'email_definitions': '/email/v1',
            'data_events': '/data/v1',
            'assets': '/assets/v1'
        },
        'documentation': 'Based on Salesforce Marketing Cloud REST API',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.before_request
def create_tables_once():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    logger.info(f"Starting Marketing Cloud API Clone on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
