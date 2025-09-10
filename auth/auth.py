import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

ACTIVE_REFRESH_TOKENS = {}

REGISTERED_CLIENTS = {
    'marketing_cloud_app_1': {
        'client_secret': hashlib.sha256('super_secret_key_123'.encode()).hexdigest(),
        'name': 'Marketing Cloud Integration',
        'permissions': ['contacts:read', 'contacts:write', 'campaigns:read', 'campaigns:write', 'emails:read',
                        'emails:write', 'data_events:read', 'data_events:write', 'assets:read']
    },
    'analytics_dashboard': {
        'client_secret': hashlib.sha256('analytics_secret_456'.encode()).hexdigest(),
        'name': 'Analytics Dashboard',
        'permissions': ['contacts:read', 'campaigns:read', 'data_events:read']
    },
    'mobile_app_client': {
        'client_secret': hashlib.sha256('mobile_secret_789'.encode()).hexdigest(),
        'name': 'Mobile Application',
        'permissions': ['contacts:read', 'assets:read']
    }
}


def generate_access_token(client_id: str, permissions: list, expires_delta: timedelta = None) -> str:
    """Gera um JWT access token"""
    if expires_delta is None:
        expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']

    expire = datetime.utcnow() + expires_delta

    payload = {
        'client_id': client_id,
        'permissions': permissions,
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'access_token',
        'jti': secrets.token_hex(16)
    }

    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    return token


def generate_refresh_token(client_id: str, permissions: list, expires_delta: timedelta = None) -> str:
    """Gera um JWT refresh token com duração mais longa"""
    if expires_delta is None:
        expires_delta = timedelta(days=1)

    expire = datetime.utcnow() + expires_delta
    jti = secrets.token_hex(16)

    payload = {
        'client_id': client_id,
        'permissions': permissions,
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'refresh_token',
        'jti': jti
    }

    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    ACTIVE_REFRESH_TOKENS[jti] = {
        'client_id': client_id,
        'created_at': datetime.utcnow(),
        'expires_at': expire,
        'is_active': True
    }

    return token


def verify_access_token(token: str) -> dict:
    """Verifica e decodifica um JWT access token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )

        if payload.get('type') != 'access_token':
            raise Exception("Invalid token type")

        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")


def verify_refresh_token(token: str) -> dict:
    """Verifica e decodifica um JWT refresh token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )

        if payload.get('type') != 'refresh_token':
            raise Exception("Invalid token type")

        jti = payload.get('jti')

        if jti not in ACTIVE_REFRESH_TOKENS:
            raise Exception("Refresh token not found")

        token_info = ACTIVE_REFRESH_TOKENS[jti]
        if not token_info['is_active']:
            raise Exception("Refresh token has been revoked")

        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Refresh token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid refresh token")


def revoke_refresh_token(jti: str) -> bool:
    """Revoga um refresh token específico"""
    if jti in ACTIVE_REFRESH_TOKENS:
        ACTIVE_REFRESH_TOKENS[jti]['is_active'] = False
        return True
    return False


def revoke_all_refresh_tokens(client_id: str) -> int:
    """Revoga todos os refresh tokens de um cliente"""
    revoked_count = 0
    for jti, token_info in ACTIVE_REFRESH_TOKENS.items():
        if token_info['client_id'] == client_id and token_info['is_active']:
            token_info['is_active'] = False
            revoked_count += 1
    return revoked_count


def cleanup_expired_tokens():
    """Remove refresh tokens expirados da memória"""
    now = datetime.utcnow()
    expired_tokens = []

    for jti, token_info in ACTIVE_REFRESH_TOKENS.items():
        if token_info['expires_at'] < now:
            expired_tokens.append(jti)

    for jti in expired_tokens:
        del ACTIVE_REFRESH_TOKENS[jti]

    return len(expired_tokens)


def require_auth(required_permission: str = None):
    """Decorator para proteger endpoints com autenticação JWT"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'error': 'Missing Authorization header',
                    'message': 'Authorization header is required',
                    'errorcode': 401
                }), 401

            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({
                    'error': 'Invalid Authorization header',
                    'message': 'Authorization header must be in format: Bearer <token>',
                    'errorcode': 401
                }), 401

            try:
                payload = verify_access_token(token)
            except Exception as e:
                return jsonify({
                    'error': 'Invalid token',
                    'message': str(e),
                    'errorcode': 401
                }), 401

            if required_permission:
                if required_permission not in payload.get('permissions', []):
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'Required permission: {required_permission}',
                        'errorcode': 403
                    }), 403

            request.jwt_payload = payload
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@auth_bp.route('/token', methods=['POST'])
def get_access_token():
    """
    Endpoint para obter access token e refresh token via Client Credentials Grant
    Simula o OAuth2 Client Credentials flow da Salesforce Marketing Cloud
    """

    if request.content_type != 'application/json':
        return jsonify({
            'error': 'Invalid Content-Type',
            'message': 'Content-Type must be application/json',
            'errorcode': 400
        }), 400

    data = request.get_json()

    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    grant_type = data.get('grant_type')

    if not all([client_id, client_secret, grant_type]):
        return jsonify({
            'error': 'Missing required fields',
            'message': 'client_id, client_secret, and grant_type are required',
            'errorcode': 400
        }), 400

    if grant_type != 'client_credentials':
        return jsonify({
            'error': 'Unsupported grant type',
            'message': 'Only client_credentials grant type is supported',
            'errorcode': 400
        }), 400

    if client_id not in REGISTERED_CLIENTS:
        return jsonify({
            'error': 'Invalid client',
            'message': 'Client ID not found',
            'errorcode': 401
        }), 401

    client_info = REGISTERED_CLIENTS[client_id]
    expected_secret = client_info['client_secret']

    provided_secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()

    if provided_secret_hash != expected_secret:
        return jsonify({
            'error': 'Invalid credentials',
            'message': 'Invalid client_secret',
            'errorcode': 401
        }), 401

    try:
        access_token = generate_access_token(
            client_id,
            client_info['permissions']
        )

        refresh_token = generate_refresh_token(
            client_id,
            client_info['permissions']
        )

        access_expires_in = int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        refresh_expires_in = int(timedelta(days=30).total_seconds())

        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': access_expires_in,
            'refresh_expires_in': refresh_expires_in,
            'scope': ' '.join(client_info['permissions']),
            'rest_instance_url': f"{request.scheme}://{request.host}",
            'client_name': client_info['name']
        }

        logger.info(f"Access and refresh tokens generated for client: {client_id}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error generating tokens: {e}")
        return jsonify({
            'error': 'Token generation failed',
            'message': 'Unable to generate tokens',
            'errorcode': 500
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_access_token():
    """
    Endpoint para renovar access token usando refresh token
    """

    if request.content_type != 'application/json':
        return jsonify({
            'error': 'Invalid Content-Type',
            'message': 'Content-Type must be application/json',
            'errorcode': 400
        }), 400

    data = request.get_json()
    refresh_token = data.get('refresh_token')
    grant_type = data.get('grant_type')

    if not refresh_token:
        return jsonify({
            'error': 'Missing refresh token',
            'message': 'refresh_token is required',
            'errorcode': 400
        }), 400

    if grant_type != 'refresh_token':
        return jsonify({
            'error': 'Invalid grant type',
            'message': 'grant_type must be refresh_token',
            'errorcode': 400
        }), 400

    try:
        payload = verify_refresh_token(refresh_token)
        client_id = payload['client_id']
        permissions = payload['permissions']

        new_access_token = generate_access_token(client_id, permissions)

        new_refresh_token = generate_refresh_token(client_id, permissions)

        old_jti = payload.get('jti')
        if old_jti:
            revoke_refresh_token(old_jti)

        access_expires_in = int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        refresh_expires_in = int(timedelta(days=30).total_seconds())

        response_data = {
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': access_expires_in,
            'refresh_expires_in': refresh_expires_in,
            'scope': ' '.join(permissions)
        }

        logger.info(f"Tokens refreshed for client: {client_id}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return jsonify({
            'error': 'Token refresh failed',
            'message': str(e),
            'errorcode': 401
        }), 401


@auth_bp.route('/revoke', methods=['POST'])
def revoke_token():
    """
    Endpoint para revogar refresh tokens
    """

    data = request.get_json()
    refresh_token = data.get('refresh_token')
    revoke_all = data.get('revoke_all', False)

    if not refresh_token:
        return jsonify({
            'error': 'Missing refresh token',
            'message': 'refresh_token is required',
            'errorcode': 400
        }), 400

    try:
        payload = verify_refresh_token(refresh_token)
        client_id = payload['client_id']
        jti = payload.get('jti')

        if revoke_all:
            revoked_count = revoke_all_refresh_tokens(client_id)
            message = f"Revoked {revoked_count} refresh tokens for client {client_id}"
        else:
            revoke_refresh_token(jti)
            message = "Refresh token revoked successfully"

        logger.info(f"Token(s) revoked for client: {client_id}")

        return jsonify({
            'revoked': True,
            'message': message
        }), 200

    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return jsonify({
            'error': 'Token revocation failed',
            'message': str(e),
            'errorcode': 400
        }), 400


@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Endpoint para verificar validade de um token"""

    data = request.get_json()
    token = data.get('token')
    token_type = data.get('token_type', 'access_token')

    if not token:
        return jsonify({
            'error': 'Missing token',
            'message': 'Token is required',
            'errorcode': 400
        }), 400

    try:
        if token_type == 'refresh_token':
            payload = verify_refresh_token(token)
        else:
            payload = verify_access_token(token)

        return jsonify({
            'valid': True,
            'token_type': payload['type'],
            'client_id': payload['client_id'],
            'permissions': payload['permissions'],
            'expires_at': payload['exp'],
            'issued_at': payload['iat']
        }), 200

    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 401


@auth_bp.route('/clients', methods=['GET'])
@require_auth()
def list_clients():
    """Listar clientes registrados (apenas para demonstração)"""

    clients_info = {}
    for client_id, info in REGISTERED_CLIENTS.items():
        clients_info[client_id] = {
            'name': info['name'],
            'permissions': info['permissions']
        }

    return jsonify({
        'clients': clients_info,
        'total': len(clients_info)
    }), 200


@auth_bp.route('/permissions', methods=['GET'])
@require_auth()
def list_permissions():
    """Listar permissões disponíveis no sistema"""

    available_permissions = [
        'contacts:read', 'contacts:write',
        'campaigns:read', 'campaigns:write',
        'emails:read', 'emails:write',
        'data_events:read', 'data_events:write',
        'assets:read', 'assets:write'
    ]

    return jsonify({
        'permissions': available_permissions,
        'client_permissions': request.jwt_payload.get('permissions', [])
    }), 200


@auth_bp.route('/tokens/active', methods=['GET'])
@require_auth()
def list_active_tokens():
    """Lista refresh tokens ativos (para debug/administração)"""

    cleaned = cleanup_expired_tokens()

    active_tokens = []
    for jti, token_info in ACTIVE_REFRESH_TOKENS.items():
        if token_info['is_active']:
            active_tokens.append({
                'jti': jti,
                'client_id': token_info['client_id'],
                'created_at': token_info['created_at'].isoformat(),
                'expires_at': token_info['expires_at'].isoformat()
            })

    return jsonify({
        'active_refresh_tokens': active_tokens,
        'total_active': len(active_tokens),
        'expired_tokens_cleaned': cleaned
    }), 200


def get_current_client():
    """Retorna informações do cliente atualmente autenticado"""
    if hasattr(request, 'jwt_payload'):
        return request.jwt_payload
    return None
