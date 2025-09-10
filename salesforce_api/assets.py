import base64
import json
import logging
import mimetypes
import os
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import func
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from auth.auth import require_auth
from models.models import db, Asset

logger = logging.getLogger(__name__)

assets_bp = Blueprint('assets', __name__)

limiter = Limiter(key_func=get_remote_address)

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'},
    'document': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
    'template': {'html', 'htm'},
    'video': {'mp4', 'avi', 'mov', 'wmv'},
    'audio': {'mp3', 'wav', 'ogg'}
}


def ensure_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename, asset_type=None):
    if '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()

    if asset_type and asset_type.lower() in ALLOWED_EXTENSIONS:
        return extension in ALLOWED_EXTENSIONS[asset_type.lower()]

    all_extensions = set()
    for extensions in ALLOWED_EXTENSIONS.values():
        all_extensions.update(extensions)

    return extension in all_extensions


def get_asset_type_from_extension(filename):
    if '.' not in filename:
        return 'Unknown'

    extension = filename.rsplit('.', 1)[1].lower()

    for asset_type, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            return asset_type.title()

    return 'Unknown'


@assets_bp.route('/assets', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('assets:write')
def create_asset():
    """
    Criar um novo asset (upload de arquivo)
    POST /assets/v1/assets
    """

    try:
        ensure_upload_folder()

        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'message': 'File is required for asset creation',
                'errorcode': 400
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'File selection is required',
                'errorcode': 400
            }), 400

        name = request.form.get('name') or file.filename
        description = request.form.get('description', '')
        asset_type = request.form.get('assetType')
        category = request.form.get('category', 'General')
        tags = request.form.get('tags', '[]')

        if not allowed_file(file.filename, asset_type):
            return jsonify({
                'error': 'Invalid file type',
                'message': f'File type not allowed for asset type: {asset_type}',
                'errorcode': 400
            }), 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'error': 'File too large',
                'message': f'File size must be less than {MAX_FILE_SIZE // (1024 * 1024)}MB',
                'errorcode': 400
            }), 400

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        file.save(file_path)

        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = 'application/octet-stream'

        if not asset_type:
            asset_type = get_asset_type_from_extension(filename)

        file_url = url_for('assets.download_asset', filename=unique_filename, _external=True)

        asset = Asset(
            name=name,
            description=description,
            asset_type=asset_type,
            file_name=filename,
            file_size=file_size,
            mime_type=mime_type,
            file_url=file_url,
            category=category
        )

        try:
            tags_list = json.loads(tags) if isinstance(tags, str) else tags
            if tags_list:
                asset.tags = json.dumps(tags_list)
        except:
            pass

        asset.file_path = file_path

        db.session.add(asset)
        db.session.commit()

        logger.info(f"Asset created: {asset.asset_id} - {filename}")

        return jsonify({
            'asset': asset.to_dict(),
            'created': True
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating asset: {e}")
        return jsonify({
            'error': 'Asset creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/<asset_id>', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('assets:read')
def get_asset(asset_id):
    """
    Obter um asset específico
    GET /assets/v1/assets/{assetId}
    """

    try:
        asset = Asset.query.filter(
            or_(Asset.asset_id == asset_id, Asset.asset_key == asset_id)
        ).first()

        if not asset:
            return jsonify({
                'error': 'Asset not found',
                'message': f'Asset with id/key {asset_id} not found',
                'errorcode': 404
            }), 404

        return jsonify({
            'asset': asset.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving asset: {e}")
        return jsonify({
            'error': 'Asset retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/<asset_id>', methods=['PATCH'])
@limiter.limit("50 per hour")
@require_auth('assets:write')
def update_asset(asset_id):
    """
    Atualizar metadados de um asset
    PATCH /assets/v1/assets/{assetId}
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        asset = Asset.query.filter(
            or_(Asset.asset_id == asset_id, Asset.asset_key == asset_id)
        ).first()

        if not asset:
            return jsonify({
                'error': 'Asset not found',
                'message': f'Asset with id/key {asset_id} not found',
                'errorcode': 404
            }), 404

        updatable_fields = ['name', 'description', 'category']

        for field in updatable_fields:
            if field in data:
                setattr(asset, field, data[field])

        if 'tags' in data:
            asset.tags = json.dumps(data['tags'])

        asset.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Asset metadata updated: {asset.asset_id}")

        return jsonify({
            'asset': asset.to_dict(),
            'updated': True
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating asset: {e}")
        return jsonify({
            'error': 'Asset update failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/<asset_id>', methods=['DELETE'])
@limiter.limit("25 per hour")
@require_auth('assets:write')
def delete_asset(asset_id):
    """
    Excluir um asset
    DELETE /assets/v1/assets/{assetId}
    """

    try:
        asset = Asset.query.filter(
            or_(Asset.asset_id == asset_id, Asset.asset_key == asset_id)
        ).first()

        if not asset:
            return jsonify({
                'error': 'Asset not found',
                'message': f'Asset with id/key {asset_id} not found',
                'errorcode': 404
            }), 404

        file_path = getattr(asset, 'file_path', None)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")

        db.session.delete(asset)
        db.session.commit()

        logger.info(f"Asset deleted: {asset_id}")

        return jsonify({
            'deleted': True,
            'assetId': asset_id
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting asset: {e}")
        return jsonify({
            'error': 'Asset deletion failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('assets:read')
def list_assets():
    """
    Listar assets com paginação e filtros
    GET /assets/v1/assets
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        asset_type_filter = request.args.get('assetType')
        category_filter = request.args.get('category')
        name_filter = request.args.get('name')

        query = Asset.query

        if asset_type_filter:
            query = query.filter(Asset.asset_type == asset_type_filter)

        if category_filter:
            query = query.filter(Asset.category == category_filter)

            query = query.filter(Asset.name.ilike(f'%{name_filter}%'))

        order_by = request.args.get('orderBy', 'created_date')
        order_direction = request.args.get('orderDirection', 'desc')

        if hasattr(Asset, order_by):
            if order_direction.lower() == 'asc':
                query = query.order_by(getattr(Asset, order_by).asc())
            else:
                query = query.order_by(getattr(Asset, order_by).desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        assets = [asset.to_dict() for asset in pagination.items]

        return jsonify({
            'assets': assets,
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'hasNext': pagination.has_next,
                'hasPrev': pagination.has_prev,
                'nextPage': pagination.next_num if pagination.has_next else None,
                'prevPage': pagination.prev_num if pagination.has_prev else None
            },
            'filters': {
                'assetType': asset_type_filter,
                'category': category_filter,
                'name': name_filter
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        return jsonify({
            'error': 'Asset listing failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/download/<filename>')
@limiter.limit("500 per hour")
def download_asset(filename):
    """
    Download de um arquivo de asset
    GET /assets/v1/assets/download/{filename}
    """

    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(file_path):
            return jsonify({
                'error': 'File not found',
                'message': 'The requested file does not exist',
                'errorcode': 404
            }), 404

        return send_file(file_path, as_attachment=False)

    except Exception as e:
        logger.error(f"Error downloading asset: {e}")
        return jsonify({
            'error': 'Asset download failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/<asset_id>/content', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('assets:read')
def get_asset_content(asset_id):
    """
    Obter conteúdo de um asset (base64 para arquivos pequenos)
    GET /assets/v1/assets/{assetId}/content
    """

    try:
        asset = Asset.query.filter(
            or_(Asset.asset_id == asset_id, Asset.asset_key == asset_id)
        ).first()

        if not asset:
            return jsonify({
                'error': 'Asset not found',
                'message': f'Asset with id/key {asset_id} not found',
                'errorcode': 404
            }), 404

        file_path = getattr(asset, 'file_path', None)
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'error': 'File not found',
                'message': 'Asset file not found on server',
                'errorcode': 404
            }), 404

        if asset.file_size > 1024 * 1024:
            return jsonify({
                'error': 'File too large',
                'message': 'File is too large for content retrieval. Use download URL instead.',
                'errorcode': 413,
                'downloadUrl': asset.file_url
            }), 413

        with open(file_path, 'rb') as f:
            file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')

        return jsonify({
            'assetId': asset.asset_id,
            'fileName': asset.file_name,
            'mimeType': asset.mime_type,
            'fileSize': asset.file_size,
            'content': base64_content,
            'encoding': 'base64'
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving asset content: {e}")
        return jsonify({
            'error': 'Asset content retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/search', methods=['POST'])
@limiter.limit("100 per hour")
@require_auth('assets:read')
def search_assets():
    """
    Buscar assets com critérios avançados
    POST /assets/v1/assets/search
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        page = data.get('page', 1)
        per_page = min(data.get('perPage', 50), 100)

        criteria = data.get('criteria', {})

        query = Asset.query

        if 'searchTerm' in criteria:
            search_term = f"%{criteria['searchTerm']}%"
            query = query.filter(
                or_(
                    Asset.name.ilike(search_term),
                    Asset.description.ilike(search_term),
                    Asset.file_name.ilike(search_term)
                )
            )

        if 'assetTypes' in criteria:
            query = query.filter(Asset.asset_type.in_(criteria['assetTypes']))

        if 'categories' in criteria:
            query = query.filter(Asset.category.in_(criteria['categories']))

        if 'sizeRange' in criteria:
            size_range = criteria['sizeRange']
            if 'min' in size_range:
                query = query.filter(Asset.file_size >= size_range['min'])
            if 'max' in size_range:
                query = query.filter(Asset.file_size <= size_range['max'])

        if 'dateRange' in criteria:
            date_range = criteria['dateRange']
            if 'startDate' in date_range:
                start_date = datetime.strptime(date_range['startDate'], '%Y-%m-%d')
                query = query.filter(Asset.created_date >= start_date)
            if 'endDate' in date_range:
                end_date = datetime.strptime(date_range['endDate'], '%Y-%m-%d')
                query = query.filter(Asset.created_date <= end_date)

        if 'tags' in criteria:
            tags = criteria['tags']
            for tag in tags:
                query = query.filter(Asset.tags.like(f'%{tag}%'))

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        assets = [asset.to_dict() for asset in pagination.items]

        return jsonify({
            'assets': assets,
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'hasNext': pagination.has_next,
                'hasPrev': pagination.has_prev
            },
            'searchCriteria': criteria
        }), 200

    except Exception as e:
        logger.error(f"Error searching assets: {e}")
        return jsonify({
            'error': 'Asset search failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/stats', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('assets:read')
def asset_statistics():
    """
    Obter estatísticas dos assets
    GET /assets/v1/assets/stats
    """

    try:
        total_assets = Asset.query.count()
        total_size = db.session.query(func.sum(Asset.file_size)).scalar() or 0

        # Assets por tipo

        type_stats = db.session.query(
            Asset.asset_type,
            func.count(Asset.id).label('count'),
            func.sum(Asset.file_size).label('total_size')
        ).group_by(Asset.asset_type).all()

        type_breakdown = []
        for asset_type, count, size in type_stats:
            type_breakdown.append({
                'type': asset_type,
                'count': count,
                'totalSize': size or 0,
                'averageSize': (size // count) if count > 0 and size else 0
            })

        category_stats = db.session.query(
            Asset.category,
            func.count(Asset.id).label('count')
        ).group_by(Asset.category).all()

        category_breakdown = [
            {'category': cat, 'count': count}
            for cat, count in category_stats
        ]

        recent_assets = Asset.query.order_by(Asset.created_date.desc()).limit(10).all()
        recent_list = [
            {
                'assetId': asset.asset_id,
                'name': asset.name,
                'type': asset.asset_type,
                'size': asset.file_size,
                'createdDate': asset.created_date.isoformat() if asset.created_date else None
            }
            for asset in recent_assets
        ]

        return jsonify({
            'summary': {
                'totalAssets': total_assets,
                'totalSize': total_size,
                'averageSize': (total_size // total_assets) if total_assets > 0 else 0
            },
            'typeBreakdown': type_breakdown,
            'categoryBreakdown': category_breakdown,
            'recentAssets': recent_list,
            'generatedAt': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error generating asset statistics: {e}")
        return jsonify({
            'error': 'Asset statistics generation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@assets_bp.route('/assets/types', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('assets:read')
def get_asset_types():
    """
    Listar tipos de assets disponíveis
    GET /assets/v1/assets/types
    """

    asset_types = [
        {
            'type': 'Image',
            'description': 'Image files for email and web use',
            'extensions': list(ALLOWED_EXTENSIONS['image']),
            'maxSize': '10MB'
        },
        {
            'type': 'Document',
            'description': 'Document files (PDF, Word, etc.)',
            'extensions': list(ALLOWED_EXTENSIONS['document']),
            'maxSize': '10MB'
        },
        {
            'type': 'Template',
            'description': 'HTML templates for emails',
            'extensions': list(ALLOWED_EXTENSIONS['template']),
            'maxSize': '10MB'
        },
        {
            'type': 'Video',
            'description': 'Video files for multimedia content',
            'extensions': list(ALLOWED_EXTENSIONS['video']),
            'maxSize': '10MB'
        },
        {
            'type': 'Audio',
            'description': 'Audio files',
            'extensions': list(ALLOWED_EXTENSIONS['audio']),
            'maxSize': '10MB'
        }
    ]

    return jsonify({
        'assetTypes': asset_types,
        'uploadLimits': {
            'maxFileSize': f"{MAX_FILE_SIZE // (1024 * 1024)}MB",
            'allowedExtensions': ALLOWED_EXTENSIONS
        }
    }), 200
