from flask import Flask
from flask_restx import Api, Namespace

from docs.schema import auth_request_model, auth_response_model, token_verify_request_model, \
    token_verify_response_model, contact_request_model, contact_response_model, contact_search_model, \
    contact_bulk_request_model, contact_statistics_model, campaign_request_model, campaign_response_model, \
    campaign_statistics_model, campaign_summary_report_model, email_definition_request_model, \
    email_definition_response_model, email_send_request_model, email_preview_request_model, data_event_request_model, \
    data_event_response_model, data_event_bulk_request_model, funnel_analysis_request_model, events_analytics_model, \
    asset_response_model, asset_search_request_model, asset_statistics_model, pagination_model, error_response_model, \
    success_response_model, health_response_model, api_info_response_model


def configure_swagger(app: Flask) -> Api:
    """
    Configura Swagger/OpenAPI para a aplicação Flask
    """

    api = Api(
        app,
        version='1.0.0',
        title='Marketing Cloud API Clone',
        description='Salesforce Marketing Cloud REST API simulation with complete documentation',
        doc='/docs/',
        prefix='/api',
        contact='Marketing Cloud API Team',
        contact_email='dev@marketingcloud.local',
        license='MIT License',
        license_url='https://opensource.org/licenses/MIT',
        authorizations={
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'JWT token. Format: Bearer <token>'
            }
        },
        security='Bearer',
        validate=True,
        ordered=True
    )

    register_models(api)

    configure_namespaces(api)

    return api


def register_models(api: Api):
    """
    Registra todos os modelos/schemas na API
    """

    api.model('AuthRequest', auth_request_model)
    api.model('AuthResponse', auth_response_model)
    api.model('TokenVerifyRequest', token_verify_request_model)
    api.model('TokenVerifyResponse', token_verify_response_model)

    api.model('ContactRequest', contact_request_model)
    api.model('ContactResponse', contact_response_model)
    api.model('ContactSearch', contact_search_model)
    api.model('ContactBulkRequest', contact_bulk_request_model)
    api.model('ContactStatistics', contact_statistics_model)

    api.model('CampaignRequest', campaign_request_model)
    api.model('CampaignResponse', campaign_response_model)
    api.model('CampaignStatistics', campaign_statistics_model)
    api.model('CampaignSummaryReport', campaign_summary_report_model)

    api.model('EmailDefinitionRequest', email_definition_request_model)
    api.model('EmailDefinitionResponse', email_definition_response_model)
    api.model('EmailSendRequest', email_send_request_model)
    api.model('EmailPreviewRequest', email_preview_request_model)

    api.model('DataEventRequest', data_event_request_model)
    api.model('DataEventResponse', data_event_response_model)
    api.model('DataEventBulkRequest', data_event_bulk_request_model)
    api.model('FunnelAnalysisRequest', funnel_analysis_request_model)
    api.model('EventsAnalytics', events_analytics_model)

    api.model('AssetResponse', asset_response_model)
    api.model('AssetSearchRequest', asset_search_request_model)
    api.model('AssetStatistics', asset_statistics_model)

    api.model('Pagination', pagination_model)
    api.model('ErrorResponse', error_response_model)
    api.model('SuccessResponse', success_response_model)
    api.model('HealthResponse', health_response_model)
    api.model('ApiInfoResponse', api_info_response_model)


def configure_namespaces(api: Api):
    """
    Configura namespaces para organização da documentação
    """

    auth_ns = Namespace(
        'Authentication',
        description='JWT authentication and authorization endpoints',
        path='/v1/auth'
    )

    contacts_ns = Namespace(
        'Contacts',
        description='Contact management operations (CRUD, search, bulk operations)',
        path='/contacts/v1'
    )

    campaigns_ns = Namespace(
        'Campaigns',
        description='Marketing campaign management and analytics',
        path='/campaigns/v1'
    )

    emails_ns = Namespace(
        'Email Definitions',
        description='Email template management and sending operations',
        path='/email/v1'
    )

    events_ns = Namespace(
        'Data Events',
        description='Event tracking and analytics for customer behavior',
        path='/data/v1'
    )

    assets_ns = Namespace(
        'Assets',
        description='Digital asset management (files, images, documents)',
        path='/assets/v1'
    )

    system_ns = Namespace(
        'System',
        description='System health, information and utility endpoints',
        path='/'
    )

    api.add_namespace(auth_ns)
    api.add_namespace(contacts_ns)
    api.add_namespace(campaigns_ns)
    api.add_namespace(emails_ns)
    api.add_namespace(events_ns)
    api.add_namespace(assets_ns)
    api.add_namespace(system_ns)

    return {
        'auth': auth_ns,
        'contacts': contacts_ns,
        'campaigns': campaigns_ns,
        'emails': emails_ns,
        'events': events_ns,
        'assets': assets_ns,
        'system': system_ns
    }


SWAGGER_UI_CONFIG = {
    'docExpansion': 'list',
    'defaultModelsExpandDepth': 2,
    'defaultModelExpandDepth': 2,
    'displayRequestDuration': True,
    'filter': True,
    'showExtensions': True,
    'showCommonExtensions': True,
    'tryItOutEnabled': True,
    'requestSnippetsEnabled': True,
    'requestSnippets': {
        'generators': {
            'curl_bash': {
                'title': 'cURL (bash)',
                'syntax': 'bash'
            },
            'curl_powershell': {
                'title': 'cURL (PowerShell)',
                'syntax': 'powershell'
            },
            'curl_cmd': {
                'title': 'cURL (CMD)',
                'syntax': 'bash'
            }
        },
        'defaultExpanded': True,
        'languages': None  # Show all languages
    }
}

CUSTOM_HEADERS = {
    'X-API-Version': {
        'description': 'API Version',
        'type': 'string',
        'default': '1.0.0'
    },
    'X-Request-ID': {
        'description': 'Unique request identifier for tracking',
        'type': 'string',
        'format': 'uuid'
    }
}

STANDARD_RESPONSES = {
    200: 'Success',
    201: 'Created successfully',
    400: 'Bad Request - Invalid input data',
    401: 'Unauthorized - Invalid or missing authentication',
    403: 'Forbidden - Insufficient permissions',
    404: 'Not Found - Resource does not exist',
    409: 'Conflict - Resource already exists',
    413: 'Payload Too Large - File or request too large',
    429: 'Too Many Requests - Rate limit exceeded',
    500: 'Internal Server Error - Unexpected server error'
}

API_EXAMPLES = {
    'auth': {
        'get_token': {
            'summary': 'Get access token for API authentication',
            'value': {
                'client_id': 'marketing_cloud_app_1',
                'client_secret': 'super_secret_key_123',
                'grant_type': 'client_credentials'
            }
        }
    },
    'contacts': {
        'create_contact': {
            'summary': 'Create a new contact with complete information',
            'value': {
                'emailAddress': 'joao.silva@email.com',
                'firstName': 'João',
                'lastName': 'Silva',
                'city': 'São Paulo',
                'state': 'SP',
                'country': 'Brazil',
                'emailOptIn': True,
                'status': 'Active'
            }
        },
        'search_contacts': {
            'summary': 'Advanced contact search example',
            'value': {
                'page': 1,
                'perPage': 50,
                'criteria': {
                    'searchTerm': 'joão',
                    'status': ['Active'],
                    'location': {
                        'cities': ['São Paulo', 'Rio de Janeiro'],
                        'states': ['SP', 'RJ']
                    },
                    'ageRange': {
                        'min': 18,
                        'max': 65
                    }
                }
            }
        }
    },
    'campaigns': {
        'create_campaign': {
            'summary': 'Create a new email marketing campaign',
            'value': {
                'name': 'Black Friday 2024',
                'description': 'Campanha promocional Black Friday com descontos especiais',
                'campaignType': 'Email',
                'subjectLine': '🔥 Black Friday: Até 70% OFF em toda loja!',
                'fromName': 'Loja Online',
                'fromEmail': 'noreply@loja.com',
                'tags': ['promo', 'black-friday', 'desconto']
            }
        }
    },
    'emails': {
        'send_email': {
            'summary': 'Send personalized emails to multiple recipients',
            'value': {
                'recipients': [
                    {
                        'email': 'cliente1@email.com',
                        'firstName': 'Ana',
                        'lastName': 'Costa',
                        'attributes': {
                            'preferredCategory': 'Eletrônicos',
                            'loyaltyTier': 'Gold'
                        }
                    },
                    {
                        'email': 'cliente2@email.com',
                        'firstName': 'Carlos',
                        'lastName': 'Santos'
                    }
                ],
                'personalization': {
                    'promocode': 'BLACKFRIDAY2024',
                    'discount': '50%'
                }
            }
        }
    },
    'events': {
        'create_event': {
            'summary': 'Track customer interaction event',
            'value': {
                'eventType': 'EmailClick',
                'contactKey': 'contact_12345',
                'source': 'Email Campaign',
                'campaignId': 'campaign_67890',
                'eventData': {
                    'url': 'https://loja.com/produto/smartphone',
                    'linkName': 'Ver Produto',
                    'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'ipAddress': '192.168.1.100'
                }
            }
        },
        'funnel_analysis': {
            'summary': 'Analyze conversion funnel for email campaign',
            'value': {
                'steps': [
                    {'eventType': 'EmailOpen', 'name': 'Email Aberto'},
                    {'eventType': 'EmailClick', 'name': 'Link Clicado'},
                    {'eventType': 'PageView', 'name': 'Página Visitada'},
                    {'eventType': 'Purchase', 'name': 'Compra Realizada'}
                ],
                'startDate': '2024-11-01',
                'endDate': '2024-11-30',
                'campaignId': 'campaign_67890'
            }
        }
    }
}
