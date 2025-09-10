import json
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import or_

from auth.auth import require_auth
from models.models import db, Campaign, CampaignStatus

logger = logging.getLogger(__name__)

campaigns_bp = Blueprint('campaigns', __name__)

limiter = Limiter(key_func=get_remote_address)


@campaigns_bp.route('/campaigns', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('campaigns:write')
def create_campaign():
    """
    Criar uma nova campanha
    POST /campaigns/v1/campaigns
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

        existing_campaign = Campaign.query.filter_by(name=name).first()
        if existing_campaign:
            return jsonify({
                'error': 'Campaign already exists',
                'message': f'Campaign with name "{name}" already exists',
                'errorcode': 409,
                'campaignId': existing_campaign.campaign_id
            }), 409

        campaign = Campaign(
            name=name,
            description=data.get('description'),
            campaign_type=data.get('campaignType', 'Email'),
            status=CampaignStatus(data.get('status', 'Draft')),
            start_date=datetime.strptime(data.get('startDate'), '%Y-%m-%dT%H:%M:%S') if data.get('startDate') else None,
            end_date=datetime.strptime(data.get('endDate'), '%Y-%m-%dT%H:%M:%S') if data.get('endDate') else None,
            subject_line=data.get('subjectLine'),
            from_name=data.get('fromName'),
            from_email=data.get('fromEmail'),
            reply_to_email=data.get('replyToEmail')
        )

        if data.get('campaignKey'):
            campaign.campaign_key = data.get('campaignKey')

        if data.get('tags'):
            campaign.tags = json.dumps(data.get('tags'))

        db.session.add(campaign)
        db.session.commit()

        logger.info(f"Campaign created: {campaign.campaign_id}")

        return jsonify({
            'campaign': campaign.to_dict(),
            'created': True
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating campaign: {e}")
        return jsonify({
            'error': 'Campaign creation failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>', methods=['GET'])
@limiter.limit("200 per hour")
@require_auth('campaigns:read')
def get_campaign(campaign_id):
    """
    Obter uma campanha específica
    GET /campaigns/v1/campaigns/{campaignId}
    """

    try:
        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        return jsonify({
            'campaign': campaign.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving campaign: {e}")
        return jsonify({
            'error': 'Campaign retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>', methods=['PATCH'])
@limiter.limit("50 per hour")
@require_auth('campaigns:write')
def update_campaign(campaign_id):
    """
    Atualizar uma campanha existente
    PATCH /campaigns/v1/campaigns/{campaignId}
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON',
                'errorcode': 400
            }), 400

        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        if campaign.status in [CampaignStatus.RUNNING, CampaignStatus.COMPLETED]:
            return jsonify({
                'error': 'Campaign cannot be modified',
                'message': f'Campaign with status {campaign.status.value} cannot be modified',
                'errorcode': 400
            }), 400

        updatable_fields = {
            'name': 'name',
            'description': 'description',
            'campaignType': 'campaign_type',
            'subjectLine': 'subject_line',
            'fromName': 'from_name',
            'fromEmail': 'from_email',
            'replyToEmail': 'reply_to_email'
        }

        for api_field, db_field in updatable_fields.items():
            if api_field in data:
                setattr(campaign, db_field, data[api_field])

        if 'status' in data:
            new_status = CampaignStatus(data['status'])

            valid_transitions = {
                CampaignStatus.DRAFT: [CampaignStatus.SCHEDULED, CampaignStatus.CANCELLED],
                CampaignStatus.SCHEDULED: [CampaignStatus.RUNNING, CampaignStatus.CANCELLED],
                CampaignStatus.RUNNING: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED],
                CampaignStatus.PAUSED: [CampaignStatus.RUNNING, CampaignStatus.CANCELLED]
            }

            if campaign.status in valid_transitions and new_status in valid_transitions[campaign.status]:
                campaign.status = new_status
            else:
                return jsonify({
                    'error': 'Invalid status transition',
                    'message': f'Cannot change status from {campaign.status.value} to {new_status.value}',
                    'errorcode': 400
                }), 400

        if 'startDate' in data and data['startDate']:
            campaign.start_date = datetime.strptime(data['startDate'], '%Y-%m-%dT%H:%M:%S')

        if 'endDate' in data and data['endDate']:
            campaign.end_date = datetime.strptime(data['endDate'], '%Y-%m-%dT%H:%M:%S')

        if 'tags' in data:
            campaign.tags = json.dumps(data['tags'])

        campaign.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Campaign updated: {campaign.campaign_id}")

        return jsonify({
            'campaign': campaign.to_dict(),
            'updated': True
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating campaign: {e}")
        return jsonify({
            'error': 'Campaign update failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>', methods=['DELETE'])
@limiter.limit("25 per hour")
@require_auth('campaigns:write')
def delete_campaign(campaign_id):
    """
    Excluir uma campanha
    DELETE /campaigns/v1/campaigns/{campaignId}
    """

    try:
        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        if campaign.status in [CampaignStatus.RUNNING, CampaignStatus.COMPLETED]:
            return jsonify({
                'error': 'Campaign cannot be deleted',
                'message': f'Campaign with status {campaign.status.value} cannot be deleted',
                'errorcode': 400
            }), 400

        db.session.delete(campaign)
        db.session.commit()

        logger.info(f"Campaign deleted: {campaign_id}")

        return jsonify({
            'deleted': True,
            'campaignId': campaign_id
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting campaign: {e}")
        return jsonify({
            'error': 'Campaign deletion failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns', methods=['GET'])
@limiter.limit("300 per hour")
@require_auth('campaigns:read')
def list_campaigns():
    """
    Listar campanhas com paginação e filtros
    GET /campaigns/v1/campaigns
    """

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        status_filter = request.args.get('status')
        campaign_type_filter = request.args.get('campaignType')
        name_filter = request.args.get('name')

        query = Campaign.query

        if status_filter:
            query = query.filter(Campaign.status == CampaignStatus(status_filter))

        if campaign_type_filter:
            query = query.filter(Campaign.campaign_type == campaign_type_filter)

        if name_filter:
            query = query.filter(Campaign.name.ilike(f'%{name_filter}%'))

        order_by = request.args.get('orderBy', 'created_date')
        order_direction = request.args.get('orderDirection', 'desc')

        if hasattr(Campaign, order_by):
            if order_direction.lower() == 'asc':
                query = query.order_by(getattr(Campaign, order_by).asc())
            else:
                query = query.order_by(getattr(Campaign, order_by).desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        campaigns = [campaign.to_dict() for campaign in pagination.items]

        return jsonify({
            'campaigns': campaigns,
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
                'campaignType': campaign_type_filter,
                'name': name_filter
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        return jsonify({
            'error': 'Campaign listing failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>/start', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('campaigns:write')
def start_campaign(campaign_id):
    """
    Iniciar uma campanha
    POST /campaigns/v1/campaigns/{campaignId}/start
    """

    try:
        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            return jsonify({
                'error': 'Campaign cannot be started',
                'message': f'Campaign with status {campaign.status.value} cannot be started',
                'errorcode': 400
            }), 400

        if not all([campaign.subject_line, campaign.from_email]):
            return jsonify({
                'error': 'Campaign configuration incomplete',
                'message': 'Subject line and from email are required to start campaign',
                'errorcode': 400
            }), 400

        campaign.status = CampaignStatus.RUNNING
        if not campaign.start_date:
            campaign.start_date = datetime.utcnow()
        campaign.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Campaign started: {campaign.campaign_id}")

        return jsonify({
            'campaign': campaign.to_dict(),
            'started': True,
            'startedAt': campaign.start_date.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting campaign: {e}")
        return jsonify({
            'error': 'Campaign start failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>/pause', methods=['POST'])
@limiter.limit("50 per hour")
@require_auth('campaigns:write')
def pause_campaign(campaign_id):
    """
    Pausar uma campanha
    POST /campaigns/v1/campaigns/{campaignId}/pause
    """

    try:
        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        if campaign.status != CampaignStatus.RUNNING:
            return jsonify({
                'error': 'Campaign cannot be paused',
                'message': f'Only running campaigns can be paused. Current status: {campaign.status.value}',
                'errorcode': 400
            }), 400

        campaign.status = CampaignStatus.PAUSED
        campaign.modified_date = datetime.utcnow()

        db.session.commit()

        logger.info(f"Campaign paused: {campaign.campaign_id}")

        return jsonify({
            'campaign': campaign.to_dict(),
            'paused': True,
            'pausedAt': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error pausing campaign: {e}")
        return jsonify({
            'error': 'Campaign pause failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/<campaign_id>/statistics', methods=['GET'])
@limiter.limit("100 per hour")
@require_auth('campaigns:read')
def get_campaign_statistics(campaign_id):
    """
    Obter estatísticas detalhadas de uma campanha
    GET /campaigns/v1/campaigns/{campaignId}/statistics
    """

    try:
        campaign = Campaign.query.filter(
            or_(Campaign.campaign_id == campaign_id, Campaign.campaign_key == campaign_id)
        ).first()

        if not campaign:
            return jsonify({
                'error': 'Campaign not found',
                'message': f'Campaign with id/key {campaign_id} not found',
                'errorcode': 404
            }), 404

        stats = {
            'campaignId': campaign.campaign_id,
            'campaignName': campaign.name,
            'status': campaign.status.value,
            'totalSent': campaign.total_sent,
            'totalOpens': campaign.total_opens,
            'totalClicks': campaign.total_clicks,
            'totalBounces': campaign.total_bounces,
            'totalUnsubscribes': campaign.total_unsubscribes,
            'uniqueOpens': int(campaign.total_opens * 0.85),  # Simulado: ~85% de opens únicos
            'uniqueClicks': int(campaign.total_clicks * 0.90),  # Simulado: ~90% de clicks únicos
            'rates': {
                'openRate': round((campaign.total_opens / campaign.total_sent * 100),
                                  2) if campaign.total_sent > 0 else 0,
                'clickRate': round((campaign.total_clicks / campaign.total_sent * 100),
                                   2) if campaign.total_sent > 0 else 0,
                'clickToOpenRate': round((campaign.total_clicks / campaign.total_opens * 100),
                                         2) if campaign.total_opens > 0 else 0,
                'bounceRate': round((campaign.total_bounces / campaign.total_sent * 100),
                                    2) if campaign.total_sent > 0 else 0,
                'unsubscribeRate': round((campaign.total_unsubscribes / campaign.total_sent * 100),
                                         2) if campaign.total_sent > 0 else 0
            },
            'performance': {
                'deliveryRate': round(((campaign.total_sent - campaign.total_bounces) / campaign.total_sent * 100),
                                      2) if campaign.total_sent > 0 else 0,
                'engagementRate': round(((campaign.total_opens + campaign.total_clicks) / campaign.total_sent * 100),
                                        2) if campaign.total_sent > 0 else 0
            },
            'timeline': {
                'createdDate': campaign.created_date.isoformat() if campaign.created_date else None,
                'startDate': campaign.start_date.isoformat() if campaign.start_date else None,
                'endDate': campaign.end_date.isoformat() if campaign.end_date else None,
                'modifiedDate': campaign.modified_date.isoformat() if campaign.modified_date else None
            }
        }

        # Adicionar comparação com benchmarks da indústria (dados simulados)
        industry_benchmarks = {
            'Email': {'openRate': 22.0, 'clickRate': 3.5, 'bounceRate': 2.0},
            'SMS': {'openRate': 95.0, 'clickRate': 15.0, 'bounceRate': 1.0},
            'Push Notification': {'openRate': 45.0, 'clickRate': 8.0, 'bounceRate': 0.5}
        }

        if campaign.campaign_type in industry_benchmarks:
            benchmark = industry_benchmarks[campaign.campaign_type]
            stats['benchmarkComparison'] = {
                'industryType': campaign.campaign_type,
                'openRateVsBenchmark': round(stats['rates']['openRate'] - benchmark['openRate'], 2),
                'clickRateVsBenchmark': round(stats['rates']['clickRate'] - benchmark['clickRate'], 2),
                'bounceRateVsBenchmark': round(stats['rates']['bounceRate'] - benchmark['bounceRate'], 2)
            }

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error retrieving campaign statistics: {e}")
        return jsonify({
            'error': 'Campaign statistics retrieval failed',
            'message': str(e),
            'errorcode': 500
        }), 500


@campaigns_bp.route('/campaigns/reports/summary', methods=['GET'])
@limiter.limit("50 per hour")
@require_auth('campaigns:read')
def campaigns_summary_report():
    """
    Relatório resumo de todas as campanhas
    GET /campaigns/v1/campaigns/reports/summary
    """

    try:
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')

        query = Campaign.query

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Campaign.created_date >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Campaign.created_date <= end_dt)

        campaigns = query.all()

        total_campaigns = len(campaigns)
        total_sent = sum(c.total_sent for c in campaigns)
        total_opens = sum(c.total_opens for c in campaigns)
        total_clicks = sum(c.total_clicks for c in campaigns)
        total_bounces = sum(c.total_bounces for c in campaigns)
        total_unsubscribes = sum(c.total_unsubscribes for c in campaigns)

        status_counts = {}
        for status in CampaignStatus:
            count = sum(1 for c in campaigns if c.status == status)
            status_counts[status.value] = count

        type_counts = {}
        for campaign in campaigns:
            campaign_type = campaign.campaign_type or 'Unknown'
            type_counts[campaign_type] = type_counts.get(campaign_type, 0) + 1

        top_campaigns = sorted(
            campaigns,
            key=lambda c: (c.total_opens + c.total_clicks) if c.total_sent > 0 else 0,
            reverse=True
        )[:5]

        summary = {
            'reportPeriod': {
                'startDate': start_date,
                'endDate': end_date,
                'generatedAt': datetime.utcnow().isoformat()
            },
            'totals': {
                'totalCampaigns': total_campaigns,
                'totalSent': total_sent,
                'totalOpens': total_opens,
                'totalClicks': total_clicks,
                'totalBounces': total_bounces,
                'totalUnsubscribes': total_unsubscribes
            },
            'averageRates': {
                'avgOpenRate': round((total_opens / total_sent * 100), 2) if total_sent > 0 else 0,
                'avgClickRate': round((total_clicks / total_sent * 100), 2) if total_sent > 0 else 0,
                'avgBounceRate': round((total_bounces / total_sent * 100), 2) if total_sent > 0 else 0,
                'avgUnsubscribeRate': round((total_unsubscribes / total_sent * 100), 2) if total_sent > 0 else 0
            },
            'statusBreakdown': status_counts,
            'typeBreakdown': type_counts,
            'topPerformingCampaigns': [
                {
                    'campaignId': c.campaign_id,
                    'name': c.name,
                    'type': c.campaign_type,
                    'totalSent': c.total_sent,
                    'openRate': round((c.total_opens / c.total_sent * 100), 2) if c.total_sent > 0 else 0,
                    'clickRate': round((c.total_clicks / c.total_sent * 100), 2) if c.total_sent > 0 else 0
                }
                for c in top_campaigns
            ]
        }

        return jsonify(summary), 200

    except Exception as e:
        logger.error(f"Error generating campaigns summary report: {e}")
        return jsonify({
            'error': 'Summary report generation failed',
            'message': str(e),
            'errorcode': 500
        }), 500
