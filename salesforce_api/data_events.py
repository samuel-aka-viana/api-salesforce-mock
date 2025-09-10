import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import func

from auth.auth import require_auth
from models.models import db, DataEvent, DataEventType, Contact

logger = logging.getLogger(__name__)

data_events_bp = Blueprint('data_events', __name__)

limiter = Limiter(key_func=get_remote_address)


@data_events_bp.route('/events', methods=['POST'])
@limiter.limit("500 per hour")
@require_auth('data_events:write')
def create_data_event():
    """
    Criar um novo evento de dados
    POST /data/v1/events
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        event_type = data.get('eventType')
        contact_key = data.get('contactKey')

        if not event_type:
            return jsonify({
                'error': 'Missing required field',
                'message': 'eventType is required',
                'errorcode': 400
            }), 400

        if not contact_key:
            return jsonify({
                'error': 'Missing required field',
                'message': 'contactKey is required',
                'errorcode': 400
            }), 400

        try:
            event_type_enum = DataEventType(event_type)
        except ValueError:
            valid_types = [e.value for e in DataEventType]
            return jsonify({
                'error': 'Invalid event type',
                'message': f'eventType must be one of: {", ".join(valid_types)}',
                'errorcode': 400
            }), 400

        contact = Contact.query.filter_by(contact_key=contact_key).first()
        if not contact:
            logger.warning(f"Event created for non-existent contact: {contact_key}")

        event = DataEvent(
            event_type=event_type_enum,
            contact_key=contact_key,
            event_date=datetime.strptime(data.get('eventDate'), '%Y-%m-%dT%H:%M:%S') if data.get(
                'eventDate') else datetime.utcnow(),
            source=data.get('source', 'API'),
            campaign_id=data.get('campaignId'),
            email_definition_id=data.get('emailDefinitionId')
        )

        if data.get('eventData'):
            event.event_data = json.dumps(data.get('eventData'))

        if data.get('eventId'):
            event.event_id = data.get('eventId')

        db.session.add(event)
        db.session.commit()

        logger.info(f"Data event created: {event.event_id} - {event_type} for {contact_key}")

        return jsonify({
            'event': event.to_dict(),
            'created': True
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating data event: {e}")
        return jsonify({
            'error': 'Data event creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/bulk', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('data_events:write')
def bulk_create_data_events():
    """
    Criar múltiplos eventos de dados de uma vez
    POST /data/v1/events/bulk
    """

    try:
        data = request.get_json()

        if not data or 'events' not in data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must contain events array',
                'errorcode': 400
            }), 400

        events_data = data['events']
        if len(events_data) > 1000:
            return jsonify({
                'error': 'Too many events',
                'message': 'Maximum 1000 events per bulk operation',
                'errorcode': 400
            }), 400

        created_events = []
        errors = []

        for i, event_data in enumerate(events_data):
            try:
                event_type = event_data.get('eventType')
                contact_key = event_data.get('contactKey')

                if not event_type or not contact_key:
                    errors.append({
                        'index': i,
                        'error': 'Missing required fields (eventType, contactKey)',
                        'data': event_data
                    })
                    continue

                try:
                    event_type_enum = DataEventType(event_type)
                except ValueError:
                    errors.append({
                        'index': i,
                        'error': f'Invalid event type: {event_type}',
                        'data': event_data
                    })
                    continue

                event = DataEvent(
                    event_type=event_type_enum,
                    contact_key=contact_key,
                    event_date=datetime.strptime(event_data.get('eventDate'), '%Y-%m-%dT%H:%M:%S') if event_data.get(
                        'eventDate') else datetime.utcnow(),
                    source=event_data.get('source', 'API'),
                    campaign_id=event_data.get('campaignId'),
                    email_definition_id=event_data.get('emailDefinitionId')
                )

                if event_data.get('eventData'):
                    event.event_data = json.dumps(event_data.get('eventData'))

                if event_data.get('eventId'):
                    event.event_id = event_data.get('eventId')

                db.session.add(event)
                created_events.append(event)

            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'data': event_data
                })

        if created_events:
            db.session.commit()

        logger.info(f"Bulk created {len(created_events)} events, {len(errors)} errors")

        return jsonify({
            'created': len(created_events),
            'errors': len(errors),
            'events': [event.to_dict() for event in created_events],
            'errorDetails': errors[:50]
        }), 201 if created_events else 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk event creation: {e}")
        return jsonify({
            'error': 'Bulk event creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/<event_id>', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('data_events:read')
def get_data_event(event_id):
    """
    Obter um evento específico
    GET /data/v1/events/{eventId}
    """

    try:
        event = DataEvent.query.filter_by(event_id=event_id).first()

        if not event:
            return jsonify({
                'error': 'Event not found',
                'message': f'Event with id {event_id} not found',
                'errorcode': 404
            }), 404

        return jsonify({
            'event': event.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving data event: {e}")
        return jsonify({
            'error': 'Event retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('data_events:read')
def list_data_events():
    """
    Listar eventos com paginação e filtros
    GET /data/v1/events
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        event_type_filter = request.args.get('eventType')
        contact_key_filter = request.args.get('contactKey')
        source_filter = request.args.get('source')
        campaign_id_filter = request.args.get('campaignId')

        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')

        query = DataEvent.query

        if event_type_filter:
            query = query.filter(DataEvent.event_type == DataEventType(event_type_filter))

        if contact_key_filter:
            query = query.filter(DataEvent.contact_key == contact_key_filter)

        if source_filter:
            query = query.filter(DataEvent.source == source_filter)

        if campaign_id_filter:
            query = query.filter(DataEvent.campaign_id == campaign_id_filter)

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DataEvent.event_date >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(DataEvent.event_date < end_dt)

        order_by = request.args.get('orderBy', 'event_date')
        order_direction = request.args.get('orderDirection', 'desc')

        if hasattr(DataEvent, order_by):
            if order_direction.lower() == 'asc':
                query = query.order_by(getattr(DataEvent, order_by).asc())
            else:
                query = query.order_by(getattr(DataEvent, order_by).desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        events = [event.to_dict() for event in pagination.items]

        return jsonify({
            'events': events,
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
                'eventType': event_type_filter,
                'contactKey': contact_key_filter,
                'source': source_filter,
                'campaignId': campaign_id_filter,
                'startDate': start_date,
                'endDate': end_date
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing data events: {e}")
        return jsonify({
            'error': 'Event listing failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/contact/<contact_key>', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('data_events:read')
def get_contact_events(contact_key):
    """
    Obter eventos de um contato específico
    GET /data/v1/events/contact/{contactKey}
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        event_type_filter = request.args.get('eventType')

        query = DataEvent.query.filter_by(contact_key=contact_key)

        if event_type_filter:
            query = query.filter(DataEvent.event_type == DataEventType(event_type_filter))

        query = query.order_by(DataEvent.event_date.desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        events = [event.to_dict() for event in pagination.items]

        contact_stats = db.session.query(
            DataEvent.event_type,
            func.count(DataEvent.id).label('count')
        ).filter_by(contact_key=contact_key).group_by(DataEvent.event_type).all()

        event_summary = {}
        for event_type, count in contact_stats:
            event_summary[event_type.value] = count

        return jsonify({
            'contactKey': contact_key,
            'events': events,
            'eventSummary': event_summary,
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'hasNext': pagination.has_next,
                'hasPrev': pagination.has_prev
            }
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving contact events: {e}")
        return jsonify({
            'error': 'Contact events retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/analytics', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('data_events:read')
def get_events_analytics():
    """
    Obter analytics dos eventos
    GET /data/v1/events/analytics
    """

    try:
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        group_by = request.args.get('groupBy', 'day')

        query = DataEvent.query

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DataEvent.event_date >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(DataEvent.event_date < end_dt)

        event_type_stats = db.session.query(
            DataEvent.event_type,
            func.count(DataEvent.id).label('count')
        ).filter(query.whereclause if query.whereclause is not None else True).group_by(DataEvent.event_type).all()

        events_by_type = {}
        total_events = 0
        for event_type, count in event_type_stats:
            events_by_type[event_type.value] = count
            total_events += count

        source_stats = db.session.query(
            DataEvent.source,
            func.count(DataEvent.id).label('count')
        ).filter(query.whereclause if query.whereclause is not None else True).group_by(DataEvent.source).all()

        events_by_source = {}
        for source, count in source_stats:
            events_by_source[source or 'Unknown'] = count

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        if group_by == 'day':
            timeline_format = func.date(DataEvent.event_date)
        elif group_by == 'hour':
            timeline_format = func.date_format(DataEvent.event_date, '%Y-%m-%d %H:00:00')
        else:
            timeline_format = func.date_format(DataEvent.event_date, '%Y-%m-01')

        timeline_stats = db.session.query(
            timeline_format.label('period'),
            DataEvent.event_type,
            func.count(DataEvent.id).label('count')
        ).filter(
            DataEvent.event_date >= thirty_days_ago
        ).group_by(
            timeline_format,
            DataEvent.event_type
        ).order_by(timeline_format).all()

        timeline = {}
        for period, event_type, count in timeline_stats:
            period_str = str(period)
            if period_str not in timeline:
                timeline[period_str] = {}
            timeline[period_str][event_type.value] = count

        top_contacts = db.session.query(
            DataEvent.contact_key,
            func.count(DataEvent.id).label('event_count')
        ).filter(
            query.whereclause if query.whereclause is not None else True
        ).group_by(
            DataEvent.contact_key
        ).order_by(
            func.count(DataEvent.id).desc()
        ).limit(10).all()

        top_contacts_list = [
            {'contactKey': contact_key, 'eventCount': count}
            for contact_key, count in top_contacts
        ]

        analytics = {
            'summary': {
                'totalEvents': total_events,
                'uniqueContacts': db.session.query(func.count(func.distinct(DataEvent.contact_key))).scalar(),
                'dateRange': {
                    'startDate': start_date,
                    'endDate': end_date
                }
            },
            'eventsByType': events_by_type,
            'eventsBySource': events_by_source,
            'timeline': timeline,
            'topContacts': top_contacts_list,
            'generatedAt': datetime.utcnow().isoformat()
        }

        return jsonify(analytics), 200

    except Exception as e:
        logger.error(f"Error generating events analytics: {e}")
        return jsonify({
            'error': 'Events analytics generation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/funnel', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('data_events:read')
def analyze_event_funnel():
    """
    Analisar funil de conversão baseado em eventos
    POST /data/v1/events/funnel
    """

    try:
        data = request.get_json()

        if not data or 'steps' not in data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must contain funnel steps',
                'errorcode': 400
            }), 400

        steps = data['steps']
        if len(steps) < 2:
            return jsonify({
                'error': 'Invalid funnel',
                'message': 'Funnel must have at least 2 steps',
                'errorcode': 400
            }), 400

        start_date = data.get('startDate')
        end_date = data.get('endDate')
        campaign_id = data.get('campaignId')

        funnel_results = []
        previous_contacts = None

        for i, step in enumerate(steps):
            step_event_type = step.get('eventType')
            step_name = step.get('name', f'Step {i + 1}')

            if not step_event_type:
                return jsonify({
                    'error': 'Invalid step',
                    'message': f'Step {i + 1} missing eventType',
                    'errorcode': 400
                }), 400

            query = db.session.query(func.distinct(DataEvent.contact_key))
            query = query.filter(DataEvent.event_type == DataEventType(step_event_type))

            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(DataEvent.event_date >= start_dt)

            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(DataEvent.event_date < end_dt)

            if campaign_id:
                query = query.filter(DataEvent.campaign_id == campaign_id)

            if previous_contacts is not None:
                query = query.filter(DataEvent.contact_key.in_(previous_contacts))

            step_contacts = [row[0] for row in query.all()]
            step_count = len(step_contacts)

            if i == 0:
                conversion_rate = 100.0
            else:
                conversion_rate = (step_count / len(previous_contacts) * 100) if previous_contacts else 0

            funnel_results.append({
                'stepNumber': i + 1,
                'stepName': step_name,
                'eventType': step_event_type,
                'contactCount': step_count,
                'conversionRate': round(conversion_rate, 2),
                'dropoffRate': round(100 - conversion_rate, 2) if i > 0 else 0
            })

            previous_contacts = step_contacts

        total_conversion = 0
        if funnel_results:
            total_conversion = (funnel_results[-1]['contactCount'] / funnel_results[0]['contactCount'] * 100) if \
                funnel_results[0]['contactCount'] > 0 else 0

        funnel_analysis = {
            'funnelSteps': funnel_results,
            'summary': {
                'totalSteps': len(steps),
                'initialContacts': funnel_results[0]['contactCount'] if funnel_results else 0,
                'finalContacts': funnel_results[-1]['contactCount'] if funnel_results else 0,
                'overallConversionRate': round(total_conversion, 2)
            },
            'filters': {
                'startDate': start_date,
                'endDate': end_date,
                'campaignId': campaign_id
            },
            'analyzedAt': datetime.utcnow().isoformat()
        }

        return jsonify(funnel_analysis), 200

    except Exception as e:
        logger.error(f"Error analyzing event funnel: {e}")
        return jsonify({
            'error': 'Funnel analysis failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@data_events_bp.route('/events/types', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('data_events:read')
def get_event_types():
    """
    Listar tipos de eventos disponíveis
    GET /data/v1/events/types
    """

    event_types = [
        {
            'type': 'EmailOpen',
            'description': 'Email was opened by recipient',
            'category': 'Email',
            'trackingRequired': True
        },
        {
            'type': 'EmailClick',
            'description': 'Link clicked in email',
            'category': 'Email',
            'trackingRequired': True
        },
        {
            'type': 'EmailBounce',
            'description': 'Email bounced',
            'category': 'Email',
            'trackingRequired': False
        },
        {
            'type': 'EmailUnsubscribe',
            'description': 'Contact unsubscribed from emails',
            'category': 'Email',
            'trackingRequired': False
        },
        {
            'type': 'Purchase',
            'description': 'Purchase or transaction completed',
            'category': 'Commerce',
            'trackingRequired': False
        },
        {
            'type': 'PageView',
            'description': 'Website page viewed',
            'category': 'Website',
            'trackingRequired': True
        },
        {
            'type': 'FormSubmission',
            'description': 'Form submitted on website',
            'category': 'Website',
            'trackingRequired': False
        }
    ]

    return jsonify({
        'eventTypes': event_types,
        'total': len(event_types)
    }), 200
