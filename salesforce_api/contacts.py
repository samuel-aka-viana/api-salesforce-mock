import json
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import or_

from auth.auth import require_auth
from models.models import db, Contact, ContactStatus

logger = logging.getLogger(__name__)

contacts_bp = Blueprint('contacts', __name__)

limiter = Limiter(key_func=get_remote_address)


@contacts_bp.route('/contacts', methods=['POST'])
@limiter.limit("100 per hour")
@require_auth('contacts:write')
def create_contact():
    """
    Criar um novo contato
    POST /contacts/v1/contacts
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        email = data.get('emailAddress')
        if not email:
            return jsonify({
                'error': 'Missing required field',
                'message': 'emailAddress is required',
                'errorcode': 400
            }), 400

        existing_contact = Contact.query.filter_by(email_address=email).first()
        if existing_contact:
            return jsonify({
                'error': 'Contact already exists',
                'message': f'Contact with email {email} already exists',
                'errorcode': 409,
                'contactKey': existing_contact.contact_key
            }), 409

        contact = Contact(
            email_address=email,
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            gender=data.get('gender'),
            birth_date=datetime.strptime(data.get('birthDate'), '%Y-%m-%d').date() if data.get('birthDate') else None,
            age=data.get('age'),
            street_address=data.get('streetAddress'),
            city=data.get('city'),
            state=data.get('state'),
            postal_code=data.get('postalCode'),
            country=data.get('country'),
            phone_number=data.get('phoneNumber'),
            mobile_number=data.get('mobileNumber'),
            status=ContactStatus(data.get('status', 'Active')),
            html_enabled=data.get('htmlEnabled', True),
            email_opt_in=data.get('emailOptIn', True),
            sms_opt_in=data.get('smsOptIn', False)
        )

        if contact.first_name and contact.last_name:
            contact.full_name = f"{contact.first_name} {contact.last_name}"

        if data.get('customAttributes'):
            contact.custom_attributes = json.dumps(data.get('customAttributes'))

        if data.get('contactKey'):
            contact.contact_key = data.get('contactKey')

        db.session.add(contact)
        db.session.commit()

        logger.info(f"Contact created: {contact.contact_key}")

        return jsonify({
            'contact': contact.to_dict(),
            'created': True
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating contact: {e}")
        return jsonify({
            'error': 'Contact creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/<contact_key>', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('contacts:read')
def get_contact(contact_key):
    """
    Obter um contato específico
    GET /contacts/v1/contacts/{contactKey}
    """

    try:
        contact = Contact.query.filter(
            or_(Contact.contact_key == contact_key, Contact.contact_id == contact_key)
        ).first()

        if not contact:
            return jsonify({
                'error': 'Contact not found',
                'message': f'Contact with key/id {contact_key} not found',
                'errorcode': 404
            }), 404

        return jsonify({
            'contact': contact.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving contact: {e}")
        return jsonify({
            'error': 'Contact retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/<contact_key>', methods=['PATCH'])
@limiter.limit("100 per hour")
@require_auth('contacts:write')
def update_contact(contact_key):
    """
    Atualizar um contato existente
    PATCH /contacts/v1/contacts/{contactKey}
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        contact = Contact.query.filter(
            or_(Contact.contact_key == contact_key, Contact.contact_id == contact_key)
        ).first()

        if not contact:
            return jsonify({
                'error': 'Contact not found',
                'message': f'Contact with key/id {contact_key} not found',
                'errorcode': 404
            }), 404

        updatable_fields = [
            'email_address', 'first_name', 'last_name', 'gender', 'age',
            'street_address', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'mobile_number', 'html_enabled', 'email_opt_in', 'sms_opt_in'
        ]

        field_mapping = {
            'emailAddress': 'email_address',
            'firstName': 'first_name',
            'lastName': 'last_name',
            'streetAddress': 'street_address',
            'postalCode': 'postal_code',
            'phoneNumber': 'phone_number',
            'mobileNumber': 'mobile_number',
            'htmlEnabled': 'html_enabled',
            'emailOptIn': 'email_opt_in',
            'smsOptIn': 'sms_opt_in'
        }

        for api_field, db_field in field_mapping.items():
            if api_field in data:
                setattr(contact, db_field, data[api_field])

        for field in ['gender', 'age', 'city', 'state', 'country']:
            if field in data:
                setattr(contact, field, data[field])

        if 'status' in data:
            contact.status = ContactStatus(data['status'])

        if 'birthDate' in data and data['birthDate']:
            contact.birth_date = datetime.strptime(data['birthDate'], '%Y-%m-%d').date()

        if contact.first_name and contact.last_name:
            contact.full_name = f"{contact.first_name} {contact.last_name}"

        if 'customAttributes' in data:
            contact.custom_attributes = json.dumps(data['customAttributes'])

        contact.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Contact updated: {contact.contact_key}")

        return jsonify({
            'contact': contact.to_dict(),
            'updated': True
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating contact: {e}")
        return jsonify({
            'error': 'Contact update failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/<contact_key>', methods=['DELETE'])
@limiter.limit("50 per hour")
@require_auth('contacts:write')
def delete_contact(contact_key):
    """
    Excluir um contato
    DELETE /contacts/v1/contacts/{contactKey}
    """

    try:
        contact = Contact.query.filter(
            or_(Contact.contact_key == contact_key, Contact.contact_id == contact_key)
        ).first()

        if not contact:
            return jsonify({
                'error': 'Contact not found',
                'message': f'Contact with key/id {contact_key} not found',
                'errorcode': 404
            }), 404

        db.session.delete(contact)
        db.session.commit()

        logger.info(f"Contact deleted: {contact_key}")

        return jsonify({
            'deleted': True,
            'contactKey': contact_key
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting contact: {e}")
        return jsonify({
            'error': 'Contact deletion failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('contacts:read')
def list_contacts():
    """
    Listar contatos com paginação e filtros
    GET /contacts/v1/contacts
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        status_filter = request.args.get('status')
        email_filter = request.args.get('email')
        city_filter = request.args.get('city')
        state_filter = request.args.get('state')
        country_filter = request.args.get('country')
        opt_in_filter = request.args.get('emailOptIn')

        query = Contact.query

        if status_filter:
            query = query.filter(Contact.status == ContactStatus(status_filter))

        if email_filter:
            query = query.filter(Contact.email_address.ilike(f'%{email_filter}%'))

        if city_filter:
            query = query.filter(Contact.city.ilike(f'%{city_filter}%'))

        if state_filter:
            query = query.filter(Contact.state.ilike(f'%{state_filter}%'))

        if country_filter:
            query = query.filter(Contact.country.ilike(f'%{country_filter}%'))

        if opt_in_filter is not None:
            opt_in_bool = opt_in_filter.lower() == 'true'
            query = query.filter(Contact.email_opt_in == opt_in_bool)

        order_by = request.args.get('orderBy', 'created_date')
        order_direction = request.args.get('orderDirection', 'desc')

        if hasattr(Contact, order_by):
            if order_direction.lower() == 'asc':
                query = query.order_by(getattr(Contact, order_by).asc())
            else:
                query = query.order_by(getattr(Contact, order_by).desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        contacts = [contact.to_dict() for contact in pagination.items]

        return jsonify({
            'contacts': contacts,
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
                'email': email_filter,
                'city': city_filter,
                'state': state_filter,
                'country': country_filter,
                'emailOptIn': opt_in_filter
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        return jsonify({
            'error': 'Contact listing failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/search', methods=['POST'])
@limiter.limit("100 per hour")
@require_auth('contacts:read')
def search_contacts():
    """
    Buscar contatos com critérios avançados
    POST /contacts/v1/contacts/search
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

        query = Contact.query

        if 'searchTerm' in criteria:
            search_term = f"%{criteria['searchTerm']}%"
            query = query.filter(
                or_(
                    Contact.email_address.ilike(search_term),
                    Contact.first_name.ilike(search_term),
                    Contact.last_name.ilike(search_term),
                    Contact.full_name.ilike(search_term)
                )
            )

        if 'status' in criteria:
            query = query.filter(Contact.status.in_([ContactStatus(s) for s in criteria['status']]))

        if 'ageRange' in criteria:
            age_range = criteria['ageRange']
            if 'min' in age_range:
                query = query.filter(Contact.age >= age_range['min'])
            if 'max' in age_range:
                query = query.filter(Contact.age <= age_range['max'])

        if 'dateRange' in criteria:
            date_range = criteria['dateRange']
            if 'startDate' in date_range:
                start_date = datetime.strptime(date_range['startDate'], '%Y-%m-%d')
                query = query.filter(Contact.created_date >= start_date)
            if 'endDate' in date_range:
                end_date = datetime.strptime(date_range['endDate'], '%Y-%m-%d')
                query = query.filter(Contact.created_date <= end_date)

        if 'location' in criteria:
            location = criteria['location']
            if 'cities' in location:
                query = query.filter(Contact.city.in_(location['cities']))
            if 'states' in location:
                query = query.filter(Contact.state.in_(location['states']))
            if 'countries' in location:
                query = query.filter(Contact.country.in_(location['countries']))

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        contacts = [contact.to_dict() for contact in pagination.items]

        return jsonify({
            'contacts': contacts,
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
        logger.error(f"Error searching contacts: {e}")
        return jsonify({
            'error': 'Contact search failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/bulk', methods=['POST'])
@limiter.limit("20 per hour")
@require_auth('contacts:write')
def bulk_create_contacts():
    """
    Criar múltiplos contatos de uma vez
    POST /contacts/v1/contacts/bulk
    """

    try:
        data = request.get_json()

        if not data or 'contacts' not in data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must contain contacts array',
                'errorcode': 400
            }), 400

        contacts_data = data['contacts']
        if len(contacts_data) > 100:
            return jsonify({
                'error': 'Too many contacts',
                'message': 'Maximum 100 contacts per bulk operation',
                'errorcode': 400
            }), 400

        created_contacts = []
        errors = []

        for i, contact_data in enumerate(contacts_data):
            try:
                email = contact_data.get('emailAddress')
                if not email:
                    errors.append({
                        'index': i,
                        'error': 'Missing emailAddress',
                        'data': contact_data
                    })
                    continue

                existing_contact = Contact.query.filter_by(email_address=email).first()
                if existing_contact:
                    errors.append({
                        'index': i,
                        'error': 'Contact already exists',
                        'contactKey': existing_contact.contact_key,
                        'data': contact_data
                    })
                    continue

                contact = Contact(
                    email_address=email,
                    first_name=contact_data.get('firstName'),
                    last_name=contact_data.get('lastName'),
                    gender=contact_data.get('gender'),
                    birth_date=datetime.strptime(contact_data.get('birthDate'), '%Y-%m-%d').date() if contact_data.get(
                        'birthDate') else None,
                    age=contact_data.get('age'),
                    street_address=contact_data.get('streetAddress'),
                    city=contact_data.get('city'),
                    state=contact_data.get('state'),
                    postal_code=contact_data.get('postalCode'),
                    country=contact_data.get('country'),
                    phone_number=contact_data.get('phoneNumber'),
                    mobile_number=contact_data.get('mobileNumber'),
                    status=ContactStatus(contact_data.get('status', 'Active')),
                    html_enabled=contact_data.get('htmlEnabled', True),
                    email_opt_in=contact_data.get('emailOptIn', True),
                    sms_opt_in=contact_data.get('smsOptIn', False)
                )

                if contact.first_name and contact.last_name:
                    contact.full_name = f"{contact.first_name} {contact.last_name}"

                if contact_data.get('customAttributes'):
                    contact.custom_attributes = json.dumps(contact_data.get('customAttributes'))

                if contact_data.get('contactKey'):
                    contact.contact_key = contact_data.get('contactKey')

                db.session.add(contact)
                created_contacts.append(contact)

            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'data': contact_data
                })

        if created_contacts:
            db.session.commit()

        logger.info(f"Bulk created {len(created_contacts)} contacts, {len(errors)} errors")

        return jsonify({
            'created': len(created_contacts),
            'errors': len(errors),
            'contacts': [contact.to_dict() for contact in created_contacts],
            'errorDetails': errors
        }), 201 if created_contacts else 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk contact creation: {e}")
        return jsonify({
            'error': 'Bulk contact creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@contacts_bp.route('/contacts/stats', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('contacts:read')
def contact_statistics():
    """
    Obter estatísticas dos contatos
    GET /contacts/v1/contacts/stats
    """

    try:
        total_contacts = Contact.query.count()

        status_counts = {}
        for status in ContactStatus:
            count = Contact.query.filter_by(status=status).count()
            status_counts[status.value] = count

        email_opt_in_count = Contact.query.filter_by(email_opt_in=True).count()
        sms_opt_in_count = Contact.query.filter_by(sms_opt_in=True).count()

        from sqlalchemy import func
        countries = db.session.query(
            Contact.country,
            func.count(Contact.id).label('count')
        ).group_by(Contact.country).order_by(func.count(Contact.id).desc()).limit(10).all()

        country_stats = [{'country': c[0], 'count': c[1]} for c in countries if c[0]]

        return jsonify({
            'totalContacts': total_contacts,
            'statusBreakdown': status_counts,
            'optInStats': {
                'emailOptIn': email_opt_in_count,
                'smsOptIn': sms_opt_in_count,
                'emailOptInRate': round((email_opt_in_count / total_contacts * 100), 2) if total_contacts > 0 else 0,
                'smsOptInRate': round((sms_opt_in_count / total_contacts * 100), 2) if total_contacts > 0 else 0
            },
            'topCountries': country_stats,
            'generatedAt': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error generating contact statistics: {e}")
        return jsonify({
            'error': 'Statistics generation failed',
            'message': str(e),
            'errorcode': 500
        }), 500
