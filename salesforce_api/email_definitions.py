import logging
import re
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import or_

from auth.auth import require_auth
from models.models import db, EmailDefinition, EmailStatus

logger = logging.getLogger(__name__)

email_definitions_bp = Blueprint('email_definitions', __name__)

limiter = Limiter(key_func=get_remote_address)


@email_definitions_bp.route('/definitions', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('emails:write')
def create_email_definition():
    """
    Criar uma nova definição de email
    POST /email/v1/definitions
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        name = data.get('name')
        if not name:
            return jsonify({
                'error': 'Missing required field',
                'message': 'name is required',
                'errorcode': 400
            }), 400

        existing_definition = EmailDefinition.query.filter_by(name=name).first()
        if existing_definition:
            return jsonify({
                'error': 'Email definition already exists',
                'message': f'Email definition with name "{name}" already exists',
                'errorcode': 409,
                'definitionId': existing_definition.definition_id
            }), 409

        from_email = data.get('fromEmail')
        if from_email and not is_valid_email(from_email):
            return jsonify({
                'error': 'Invalid email format',
                'message': 'fromEmail must be a valid email address',
                'errorcode': 400
            }), 400

        email_def = EmailDefinition(
            name=name,
            description=data.get('description'),
            subject=data.get('subject'),
            html_content=data.get('htmlContent'),
            text_content=data.get('textContent'),
            status=EmailStatus(data.get('status', 'Draft')),
            email_type=data.get('emailType', 'Marketing'),
            from_name=data.get('fromName'),
            from_email=from_email,
            reply_to_email=data.get('replyToEmail'),
            track_opens=data.get('trackOpens', True),
            track_clicks=data.get('trackClicks', True)
        )

        if data.get('definitionKey'):
            email_def.definition_key = data.get('definitionKey')
        if email_def.html_content:
            validation_result = validate_html_content(email_def.html_content)
            if not validation_result['valid']:
                return jsonify({
                    'error': 'Invalid HTML content',
                    'message': validation_result['message'],
                    'errorcode': 400
                }), 400

        db.session.add(email_def)
        db.session.commit()

        logger.info(f"Email definition created: {email_def.definition_id}")

        return jsonify({
            'emailDefinition': email_def.to_dict(),
            'created': True
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating email definition: {e}")
        return jsonify({
            'error': 'Email definition creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('emails:read')
def get_email_definition(definition_id):
    """
    Obter uma definição de email específica
    GET /email/v1/definitions/{definitionId}
    """

    try:
        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        return jsonify({
            'emailDefinition': email_def.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving email definition: {e}")
        return jsonify({
            'error': 'Email definition retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>', methods=['PATCH'])
@limiter.limit("50 per hour")
@require_auth('emails:write')
def update_email_definition(definition_id):
    """
    Atualizar uma definição de email existente
    PATCH /email/v1/definitions/{definitionId}
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        if email_def.status == EmailStatus.ACTIVE:
            allowed_fields = ['description', 'trackOpens', 'trackClicks']
            for field in data.keys():
                if field not in allowed_fields:
                    return jsonify({
                        'error': 'Email definition cannot be fully modified',
                        'message': f'Active email definitions can only modify: {", ".join(allowed_fields)}',
                        'errorcode': 400
                    }), 400

        updatable_fields = {
            'name': 'name',
            'description': 'description',
            'subject': 'subject',
            'htmlContent': 'html_content',
            'textContent': 'text_content',
            'emailType': 'email_type',
            'fromName': 'from_name',
            'fromEmail': 'from_email',
            'replyToEmail': 'reply_to_email',
            'trackOpens': 'track_opens',
            'trackClicks': 'track_clicks'
        }

        for api_field, db_field in updatable_fields.items():
            if api_field in data:
                if api_field == 'fromEmail' and data[api_field]:
                    if not is_valid_email(data[api_field]):
                        return jsonify({
                            'error': 'Invalid email format',
                            'message': 'fromEmail must be a valid email address',
                            'errorcode': 400
                        }), 400

                if api_field == 'htmlContent' and data[api_field]:
                    validation_result = validate_html_content(data[api_field])
                    if not validation_result['valid']:
                        return jsonify({
                            'error': 'Invalid HTML content',
                            'message': validation_result['message'],
                            'errorcode': 400
                        }), 400

                setattr(email_def, db_field, data[api_field])

        if 'status' in data:
            new_status = EmailStatus(data['status'])

            valid_transitions = {
                EmailStatus.DRAFT: [EmailStatus.ACTIVE, EmailStatus.ARCHIVED],
                EmailStatus.ACTIVE: [EmailStatus.INACTIVE, EmailStatus.ARCHIVED],
                EmailStatus.INACTIVE: [EmailStatus.ACTIVE, EmailStatus.ARCHIVED]
            }

            if email_def.status in valid_transitions and new_status in valid_transitions[email_def.status]:
                email_def.status = new_status
            else:
                return jsonify({
                    'error': 'Invalid status transition',
                    'message': f'Cannot change status from {email_def.status.value} to {new_status.value}',
                    'errorcode': 400
                }), 400

        email_def.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Email definition updated: {email_def.definition_id}")

        return jsonify({
            'emailDefinition': email_def.to_dict(),
            'updated': True
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating email definition: {e}")
        return jsonify({
            'error': 'Email definition update failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>', methods=['DELETE'])
@limiter.limit("25 per hour")
@require_auth('emails:write')
def delete_email_definition(definition_id):
    """
    Excluir uma definição de email
    DELETE /email/v1/definitions/{definitionId}
    """

    try:
        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        if email_def.status == EmailStatus.ACTIVE:
            return jsonify({
                'error': 'Email definition cannot be deleted',
                'message': 'Active email definitions cannot be deleted. Please deactivate first.',
                'errorcode': 400
            }), 400

        db.session.delete(email_def)
        db.session.commit()

        logger.info(f"Email definition deleted: {definition_id}")

        return jsonify({
            'deleted': True,
            'definitionId': definition_id
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting email definition: {e}")
        return jsonify({
            'error': 'Email definition deletion failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('emails:read')
def list_email_definitions():
    """
    Listar definições de email com paginação e filtros
    GET /email/v1/definitions
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        status_filter = request.args.get('status')
        email_type_filter = request.args.get('emailType')
        name_filter = request.args.get('name')

        query = EmailDefinition.query

        if status_filter:
            query = query.filter(EmailDefinition.status == EmailStatus(status_filter))

        if email_type_filter:
            query = query.filter(EmailDefinition.email_type == email_type_filter)

        if name_filter:
            query = query.filter(EmailDefinition.name.ilike(f'%{name_filter}%'))

        order_by = request.args.get('orderBy', 'created_date')
        order_direction = request.args.get('orderDirection', 'desc')

        if hasattr(EmailDefinition, order_by):
            if order_direction.lower() == 'asc':
                query = query.order_by(getattr(EmailDefinition, order_by).asc())
            else:
                query = query.order_by(getattr(EmailDefinition, order_by).desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        email_definitions = [email_def.to_dict() for email_def in pagination.items]

        return jsonify({
            'emailDefinitions': email_definitions,
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
                'status': status_filter,
                'emailType': email_type_filter,
                'name': name_filter
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing email definitions: {e}")
        return jsonify({
            'error': 'Email definition listing failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>/send', methods=['POST'])
@limiter.limit("100 per hour")
@require_auth('emails:write')
def send_email_definition(definition_id):
    """
    Enviar email baseado em uma definição (triggered send)
    POST /email/v1/definitions/{definitionId}/send
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        if email_def.status != EmailStatus.ACTIVE:
            return jsonify({
                'error': 'Email definition not active',
                'message': 'Only active email definitions can be sent',
                'errorcode': 400
            }), 400

        recipients = data.get('recipients', [])
        if not recipients:
            return jsonify({
                'error': 'No recipients specified',
                'message': 'At least one recipient is required',
                'errorcode': 400
            }), 400

        if len(recipients) > 100:
            return jsonify({
                'error': 'Too many recipients',
                'message': 'Maximum 100 recipients per send',
                'errorcode': 400
            }), 400

        processed_recipients = []
        errors = []

        for i, recipient in enumerate(recipients):
            if not isinstance(recipient, dict):
                errors.append({
                    'index': i,
                    'error': 'Invalid recipient format',
                    'recipient': recipient
                })
                continue

            email = recipient.get('email')
            if not email or not is_valid_email(email):
                errors.append({
                    'index': i,
                    'error': 'Invalid email address',
                    'recipient': recipient
                })
                continue

            processed_recipients.append({
                'email': email,
                'contactKey': recipient.get('contactKey'),
                'firstName': recipient.get('firstName'),
                'lastName': recipient.get('lastName'),
                'attributes': recipient.get('attributes', {})
            })

        if not processed_recipients:
            return jsonify({
                'error': 'No valid recipients',
                'message': 'All recipients have validation errors',
                'errorcode': 400,
                'recipientErrors': errors
            }), 400

        import uuid
        send_id = str(uuid.uuid4())

        personalization = data.get('personalization', {})
        send_time = data.get('sendTime')

        send_response = {
            'sendId': send_id,
            'definitionId': email_def.definition_id,
            'definitionName': email_def.name,
            'status': 'Queued' if send_time else 'Sent',
            'recipientCount': len(processed_recipients),
            'validRecipients': len(processed_recipients),
            'invalidRecipients': len(errors),
            'sentAt': datetime.utcnow().isoformat(),
            'scheduledFor': send_time,
            'personalization': personalization,
            'tracking': {
                'trackOpens': email_def.track_opens,
                'trackClicks': email_def.track_clicks
            }
        }

        if errors:
            send_response['recipientErrors'] = errors

        logger.info(f"Email sent from definition {definition_id}: {send_id}")

        return jsonify(send_response), 200

    except Exception as e:
        logger.error(f"Error sending email definition: {e}")
        return jsonify({
            'error': 'Email send failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>/preview', methods=['POST'])
@limiter.limit("100 per hour")
@require_auth('emails:read')
def preview_email_definition(definition_id):
    """
    Gerar preview de uma definição de email
    POST /email/v1/definitions/{definitionId}/preview
    """

    try:
        data = request.get_json() or {}

        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        preview_data = data.get('previewData', {
            'firstName': 'João',
            'lastName': 'Silva',
            'email': 'joao.silva@example.com',
            'company': 'Empresa Exemplo'
        })

        html_content = email_def.html_content or ''
        text_content = email_def.text_content or ''
        subject = email_def.subject or ''

        for key, value in preview_data.items():
            placeholder = f'{{{{{key}}}}}'
            html_content = html_content.replace(placeholder, str(value))
            text_content = text_content.replace(placeholder, str(value))
            subject = subject.replace(placeholder, str(value))

        preview_response = {
            'definitionId': email_def.definition_id,
            'definitionName': email_def.name,
            'preview': {
                'subject': subject,
                'fromName': email_def.from_name,
                'fromEmail': email_def.from_email,
                'replyToEmail': email_def.reply_to_email,
                'htmlContent': html_content,
                'textContent': text_content
            },
            'previewData': preview_data,
            'generatedAt': datetime.utcnow().isoformat()
        }

        return jsonify(preview_response), 200

    except Exception as e:
        logger.error(f"Error generating email preview: {e}")
        return jsonify({
            'error': 'Email preview generation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@email_definitions_bp.route('/definitions/<definition_id>/validate', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('emails:read')
def validate_email_definition(definition_id):
    """
    Validar uma definição de email
    POST /email/v1/definitions/{definitionId}/validate
    """

    try:
        email_def = EmailDefinition.query.filter(
            or_(EmailDefinition.definition_id == definition_id, EmailDefinition.definition_key == definition_id)
        ).first()

        if not email_def:
            return jsonify({
                'error': 'Email definition not found',
                'message': f'Email definition with id/key {definition_id} not found',
                'errorcode': 404
            }), 404

        validation_results = []

        if not email_def.subject:
            validation_results.append({
                'type': 'error',
                'field': 'subject',
                'message': 'Subject line is required'
            })

        if not email_def.from_email:
            validation_results.append({
                'type': 'error',
                'field': 'fromEmail',
                'message': 'From email is required'
            })
        elif not is_valid_email(email_def.from_email):
            validation_results.append({
                'type': 'error',
                'field': 'fromEmail',
                'message': 'From email format is invalid'
            })

        if not email_def.html_content and not email_def.text_content:
            validation_results.append({
                'type': 'error',
                'field': 'content',
                'message': 'Either HTML content or text content is required'
            })

        if email_def.html_content:
            html_validation = validate_html_content(email_def.html_content)
            if not html_validation['valid']:
                validation_results.append({
                    'type': 'error',
                    'field': 'htmlContent',
                    'message': html_validation['message']
                })

        if email_def.subject and len(email_def.subject) > 50:
            validation_results.append({
                'type': 'warning',
                'field': 'subject',
                'message': 'Subject line is longer than 50 characters and may be truncated in some email clients'
            })

        if not email_def.from_name:
            validation_results.append({
                'type': 'warning',
                'field': 'fromName',
                'message': 'From name is recommended for better deliverability'
            })

        if not email_def.text_content and email_def.html_content:
            validation_results.append({
                'type': 'warning',
                'field': 'textContent',
                'message': 'Text version is recommended for better accessibility and deliverability'
            })

        has_errors = any(r['type'] == 'error' for r in validation_results)
        has_warnings = any(r['type'] == 'warning' for r in validation_results)

        if not has_errors and not has_warnings:
            overall_status = 'valid'
        elif has_errors:
            overall_status = 'invalid'
        else:
            overall_status = 'valid_with_warnings'

        validation_response = {
            'definitionId': email_def.definition_id,
            'definitionName': email_def.name,
            'validationStatus': overall_status,
            'canSend': not has_errors,
            'validationResults': validation_results,
            'summary': {
                'totalIssues': len(validation_results),
                'errors': sum(1 for r in validation_results if r['type'] == 'error'),
                'warnings': sum(1 for r in validation_results if r['type'] == 'warning')
            },
            'validatedAt': datetime.utcnow().isoformat()
        }

        return jsonify(validation_response), 200

    except Exception as e:
        logger.error(f"Error validating email definition: {e}")
        return jsonify({
            'error': 'Email definition validation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


def is_valid_email(email):
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_html_content(html_content):
    """Validar conteúdo HTML básico"""
    try:
        if not html_content.strip():
            return {'valid': False, 'message': 'HTML content cannot be empty'}

        if '<html>' in html_content.lower() and '</html>' not in html_content.lower():
            return {'valid': False, 'message': 'HTML tag is not properly closed'}

        if '<body>' in html_content.lower() and '</body>' not in html_content.lower():
            return {'valid': False, 'message': 'Body tag is not properly closed'}

        dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
        for pattern in dangerous_patterns:
            if pattern in html_content.lower():
                return {'valid': False, 'message': f'Potentially dangerous content detected: {pattern}'}

        return {'valid': True, 'message': 'HTML content is valid'}

    except Exception as e:
        return {'valid': False, 'message': f'HTML validation error: {str(e)}'}


@email_definitions_bp.route('/types', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('emails:read')
def get_email_types():
    """
    Listar tipos de email disponíveis
    GET /email/v1/types
    """

    email_types = [
        {
            'type': 'Marketing',
            'description': 'Marketing and promotional emails',
            'features': ['Bulk sending', 'Analytics', 'A/B testing']
        },
        {
            'type': 'Transactional',
            'description': 'Transaction-related emails (receipts, confirmations)',
            'features': ['High deliverability', 'Real-time sending', 'Personalization']
        },
        {
            'type': 'Welcome',
            'description': 'Welcome series and onboarding emails',
            'features': ['Automated sequences', 'Triggered sending', 'Personalization']
        },
        {
            'type': 'Triggered',
            'description': 'Event-triggered emails',
            'features': ['Real-time triggers', 'Dynamic content', 'Behavioral targeting']
        },
        {
            'type': 'Newsletter',
            'description': 'Regular newsletter communications',
            'features': ['Scheduled sending', 'Content templates', 'Subscriber management']
        }
    ]

    return jsonify({
        'emailTypes': email_types,
        'total': len(email_types)
    }), 200
