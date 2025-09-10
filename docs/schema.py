from flask_restx import fields



auth_request_model = {
    'client_id': fields.String(required=True, description='Client ID', example='marketing_cloud_app_1'),
    'client_secret': fields.String(required=True, description='Client Secret', example='super_secret_key_123'),
    'grant_type': fields.String(required=True, description='Grant Type', example='client_credentials')
}

auth_response_model = {
    'access_token': fields.String(description='JWT Access Token'),
    'token_type': fields.String(description='Token Type', example='Bearer'),
    'expires_in': fields.Integer(description='Token expiration in seconds', example=7200),
    'scope': fields.String(description='Token permissions'),
    'rest_instance_url': fields.String(description='API Base URL'),
    'client_name': fields.String(description='Client Application Name')
}

token_verify_request_model = {
    'token': fields.String(required=True, description='JWT Token to verify')
}

token_verify_response_model = {
    'valid': fields.Boolean(description='Token validity status'),
    'client_id': fields.String(description='Client ID from token'),
    'permissions': fields.List(fields.String, description='Token permissions'),
    'expires_at': fields.Integer(description='Token expiration timestamp'),
    'issued_at': fields.Integer(description='Token issue timestamp')
}

contact_request_model = {
    'emailAddress': fields.String(required=True, description='Contact email address', example='joao.silva@email.com'),
    'firstName': fields.String(description='First name', example='João'),
    'lastName': fields.String(description='Last name', example='Silva'),
    'gender': fields.String(description='Gender', example='Male'),
    'birthDate': fields.String(description='Birth date (YYYY-MM-DD)', example='1990-05-15'),
    'age': fields.Integer(description='Age', example=33),
    'streetAddress': fields.String(description='Street address', example='Rua das Flores, 123'),
    'city': fields.String(description='City', example='São Paulo'),
    'state': fields.String(description='State', example='SP'),
    'postalCode': fields.String(description='Postal code', example='01234-567'),
    'country': fields.String(description='Country', example='Brazil'),
    'phoneNumber': fields.String(description='Phone number', example='+55 11 99999-9999'),
    'mobileNumber': fields.String(description='Mobile number', example='+55 11 88888-8888'),
    'status': fields.String(description='Contact status', enum=['Active', 'Unsubscribed', 'Bounced', 'Held'],
                            example='Active'),
    'htmlEnabled': fields.Boolean(description='HTML email preference', example=True),
    'emailOptIn': fields.Boolean(description='Email opt-in status', example=True),
    'smsOptIn': fields.Boolean(description='SMS opt-in status', example=False),
    'contactKey': fields.String(description='Custom contact key'),
    'customAttributes': fields.Raw(description='Custom attributes object')
}

contact_response_model = {
    'contactKey': fields.String(description='Unique contact key'),
    'contactId': fields.String(description='Contact ID'),
    'emailAddress': fields.String(description='Email address'),
    'firstName': fields.String(description='First name'),
    'lastName': fields.String(description='Last name'),
    'fullName': fields.String(description='Full name'),
    'gender': fields.String(description='Gender'),
    'birthDate': fields.String(description='Birth date'),
    'age': fields.Integer(description='Age'),
    'streetAddress': fields.String(description='Street address'),
    'city': fields.String(description='City'),
    'state': fields.String(description='State'),
    'postalCode': fields.String(description='Postal code'),
    'country': fields.String(description='Country'),
    'phoneNumber': fields.String(description='Phone number'),
    'mobileNumber': fields.String(description='Mobile number'),
    'status': fields.String(description='Contact status'),
    'htmlEnabled': fields.Boolean(description='HTML enabled'),
    'emailOptIn': fields.Boolean(description='Email opt-in'),
    'smsOptIn': fields.Boolean(description='SMS opt-in'),
    'createdDate': fields.String(description='Creation date'),
    'modifiedDate': fields.String(description='Last modification date'),
    'lastActivityDate': fields.String(description='Last activity date'),
    'customAttributes': fields.Raw(description='Custom attributes')
}

contact_search_model = {
    'page': fields.Integer(description='Page number', example=1),
    'perPage': fields.Integer(description='Items per page', example=50),
    'criteria': fields.Raw(description='Search criteria object', example={
        'searchTerm': 'joão',
        'status': ['Active'],
        'ageRange': {'min': 18, 'max': 65},
        'dateRange': {'startDate': '2024-01-01', 'endDate': '2024-12-31'},
        'location': {'cities': ['São Paulo'], 'states': ['SP'], 'countries': ['Brazil']}
    })
}

contact_bulk_request_model = {
    'contacts': fields.List(fields.Nested(contact_request_model), required=True,
                            description='Array of contacts to create')
}

campaign_request_model = {
    'name': fields.String(required=True, description='Campaign name', example='Black Friday 2024'),
    'description': fields.String(description='Campaign description', example='Campanha promocional Black Friday'),
    'campaignType': fields.String(description='Campaign type', example='Email'),
    'status': fields.String(description='Campaign status',
                            enum=['Draft', 'Scheduled', 'Running', 'Paused', 'Completed', 'Cancelled'],
                            example='Draft'),
    'startDate': fields.String(description='Start date (ISO format)', example='2024-11-24T09:00:00'),
    'endDate': fields.String(description='End date (ISO format)', example='2024-11-30T23:59:59'),
    'subjectLine': fields.String(description='Email subject line', example='🔥 Black Friday: Até 70% OFF!'),
    'fromName': fields.String(description='Sender name', example='Loja Online'),
    'fromEmail': fields.String(description='Sender email', example='noreply@loja.com'),
    'replyToEmail': fields.String(description='Reply-to email', example='contato@loja.com'),
    'campaignKey': fields.String(description='Custom campaign key'),
    'tags': fields.List(fields.String, description='Campaign tags', example=['promo', 'black-friday'])
}

campaign_response_model = {
    'campaignId': fields.String(description='Campaign ID'),
    'campaignKey': fields.String(description='Campaign key'),
    'name': fields.String(description='Campaign name'),
    'description': fields.String(description='Campaign description'),
    'campaignType': fields.String(description='Campaign type'),
    'status': fields.String(description='Campaign status'),
    'createdDate': fields.String(description='Creation date'),
    'modifiedDate': fields.String(description='Modification date'),
    'startDate': fields.String(description='Start date'),
    'endDate': fields.String(description='End date'),
    'subjectLine': fields.String(description='Subject line'),
    'fromName': fields.String(description='From name'),
    'fromEmail': fields.String(description='From email'),
    'replyToEmail': fields.String(description='Reply-to email'),
    'statistics': fields.Raw(description='Campaign statistics'),
    'tags': fields.List(fields.String, description='Tags')
}

campaign_statistics_model = {
    'campaignId': fields.String(description='Campaign ID'),
    'campaignName': fields.String(description='Campaign name'),
    'status': fields.String(description='Campaign status'),
    'totalSent': fields.Integer(description='Total emails sent'),
    'totalOpens': fields.Integer(description='Total opens'),
    'totalClicks': fields.Integer(description='Total clicks'),
    'totalBounces': fields.Integer(description='Total bounces'),
    'totalUnsubscribes': fields.Integer(description='Total unsubscribes'),
    'uniqueOpens': fields.Integer(description='Unique opens'),
    'uniqueClicks': fields.Integer(description='Unique clicks'),
    'rates': fields.Raw(description='Performance rates'),
    'performance': fields.Raw(description='Performance metrics'),
    'timeline': fields.Raw(description='Campaign timeline'),
    'benchmarkComparison': fields.Raw(description='Industry benchmark comparison')
}

email_definition_request_model = {
    'name': fields.String(required=True, description='Email definition name', example='Welcome Email Template'),
    'description': fields.String(description='Description', example='Email de boas-vindas para novos usuários'),
    'subject': fields.String(description='Email subject', example='Bem-vindo ao nosso serviço!'),
    'htmlContent': fields.String(description='HTML email content'),
    'textContent': fields.String(description='Plain text email content'),
    'status': fields.String(description='Definition status', enum=['Draft', 'Active', 'Inactive', 'Archived'],
                            example='Draft'),
    'emailType': fields.String(description='Email type', example='Welcome'),
    'fromName': fields.String(description='From name', example='Equipe Suporte'),
    'fromEmail': fields.String(description='From email', example='suporte@empresa.com'),
    'replyToEmail': fields.String(description='Reply-to email', example='contato@empresa.com'),
    'trackOpens': fields.Boolean(description='Track email opens', example=True),
    'trackClicks': fields.Boolean(description='Track link clicks', example=True),
    'definitionKey': fields.String(description='Custom definition key')
}

email_definition_response_model = {
    'definitionKey': fields.String(description='Definition key'),
    'definitionId': fields.String(description='Definition ID'),
    'name': fields.String(description='Name'),
    'description': fields.String(description='Description'),
    'subject': fields.String(description='Subject'),
    'htmlContent': fields.String(description='HTML content'),
    'textContent': fields.String(description='Text content'),
    'status': fields.String(description='Status'),
    'emailType': fields.String(description='Email type'),
    'fromName': fields.String(description='From name'),
    'fromEmail': fields.String(description='From email'),
    'replyToEmail': fields.String(description='Reply-to email'),
    'createdDate': fields.String(description='Creation date'),
    'modifiedDate': fields.String(description='Modification date'),
    'trackOpens': fields.Boolean(description='Track opens'),
    'trackClicks': fields.Boolean(description='Track clicks')
}

email_send_request_model = {
    'recipients': fields.List(fields.Raw, required=True, description='List of recipients', example=[
        {
            'email': 'usuario@email.com',
            'contactKey': 'contact_123',
            'firstName': 'João',
            'lastName': 'Silva',
            'attributes': {'customField': 'value'}
        }
    ]),
    'personalization': fields.Raw(description='Personalization data'),
    'sendTime': fields.String(description='Scheduled send time (ISO format)')
}

email_preview_request_model = {
    'previewData': fields.Raw(description='Data for preview personalization', example={
        'firstName': 'João',
        'lastName': 'Silva',
        'email': 'joao.silva@email.com',
        'company': 'Empresa Exemplo'
    })
}

data_event_request_model = {
    'eventType': fields.String(required=True, description='Event type',
                               enum=['EmailOpen', 'EmailClick', 'EmailBounce', 'EmailUnsubscribe', 'Purchase',
                                     'PageView', 'FormSubmission'],
                               example='EmailOpen'),
    'contactKey': fields.String(required=True, description='Contact key', example='contact_123'),
    'eventDate': fields.String(description='Event date (ISO format)', example='2024-01-15T10:30:00'),
    'source': fields.String(description='Event source', example='Website'),
    'campaignId': fields.String(description='Associated campaign ID'),
    'emailDefinitionId': fields.String(description='Associated email definition ID'),
    'eventData': fields.Raw(description='Additional event data', example={
        'userAgent': 'Mozilla/5.0...',
        'ipAddress': '192.168.1.1',
        'url': 'https://site.com/produto'
    }),
    'eventId': fields.String(description='Custom event ID')
}

data_event_response_model = {
    'eventId': fields.String(description='Event ID'),
    'eventType': fields.String(description='Event type'),
    'contactKey': fields.String(description='Contact key'),
    'eventDate': fields.String(description='Event date'),
    'createdDate': fields.String(description='Creation date'),
    'eventData': fields.Raw(description='Event data'),
    'source': fields.String(description='Event source'),
    'campaignId': fields.String(description='Campaign ID'),
    'emailDefinitionId': fields.String(description='Email definition ID')
}

data_event_bulk_request_model = {
    'events': fields.List(fields.Nested(data_event_request_model), required=True,
                          description='Array of events to create')
}

funnel_analysis_request_model = {
    'steps': fields.List(fields.Raw, required=True, description='Funnel steps', example=[
        {'eventType': 'EmailOpen', 'name': 'Email Opened'},
        {'eventType': 'EmailClick', 'name': 'Email Clicked'},
        {'eventType': 'Purchase', 'name': 'Purchase Completed'}
    ]),
    'startDate': fields.String(description='Analysis start date'),
    'endDate': fields.String(description='Analysis end date'),
    'campaignId': fields.String(description='Filter by campaign ID')
}

asset_response_model = {
    'assetId': fields.String(description='Asset ID'),
    'assetKey': fields.String(description='Asset key'),
    'name': fields.String(description='Asset name'),
    'description': fields.String(description='Asset description'),
    'assetType': fields.String(description='Asset type'),
    'fileName': fields.String(description='Original file name'),
    'fileSize': fields.Integer(description='File size in bytes'),
    'mimeType': fields.String(description='MIME type'),
    'fileUrl': fields.String(description='Download URL'),
    'createdDate': fields.String(description='Creation date'),
    'modifiedDate': fields.String(description='Modification date'),
    'tags': fields.List(fields.String, description='Asset tags'),
    'category': fields.String(description='Asset category')
}

asset_search_request_model = {
    'page': fields.Integer(description='Page number', example=1),
    'perPage': fields.Integer(description='Items per page', example=50),
    'criteria': fields.Raw(description='Search criteria', example={
        'searchTerm': 'logo',
        'assetTypes': ['Image'],
        'categories': ['Marketing'],
        'sizeRange': {'min': 1024, 'max': 1048576},
        'dateRange': {'startDate': '2024-01-01', 'endDate': '2024-12-31'},
        'tags': ['brand', 'campaign']
    })
}

pagination_model = {
    'page': fields.Integer(description='Current page number'),
    'perPage': fields.Integer(description='Items per page'),
    'total': fields.Integer(description='Total items'),
    'pages': fields.Integer(description='Total pages'),
    'hasNext': fields.Boolean(description='Has next page'),
    'hasPrev': fields.Boolean(description='Has previous page'),
    'nextPage': fields.Integer(description='Next page number'),
    'prevPage': fields.Integer(description='Previous page number')
}

error_response_model = {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message'),
    'errorcode': fields.Integer(description='Error code')
}

success_response_model = {
    'success': fields.Boolean(description='Success status'),
    'message': fields.String(description='Success message')
}

health_response_model = {
    'status': fields.String(description='Service status', example='healthy'),
    'timestamp': fields.String(description='Response timestamp'),
    'version': fields.String(description='API version', example='1.0.0'),
    'service': fields.String(description='Service name', example='Marketing Cloud API Clone')
}

api_info_response_model = {
    'name': fields.String(description='API name'),
    'version': fields.String(description='API version'),
    'description': fields.String(description='API description'),
    'endpoints': fields.Raw(description='Available endpoints'),
    'documentation': fields.String(description='Documentation reference'),
    'timestamp': fields.String(description='Response timestamp')
}

contact_statistics_model = {
    'totalContacts': fields.Integer(description='Total number of contacts'),
    'statusBreakdown': fields.Raw(description='Contacts by status'),
    'optInStats': fields.Raw(description='Opt-in statistics'),
    'topCountries': fields.List(fields.Raw, description='Top countries by contact count'),
    'generatedAt': fields.String(description='Report generation timestamp')
}

campaign_summary_report_model = {
    'reportPeriod': fields.Raw(description='Report period information'),
    'totals': fields.Raw(description='Campaign totals'),
    'averageRates': fields.Raw(description='Average performance rates'),
    'statusBreakdown': fields.Raw(description='Campaigns by status'),
    'typeBreakdown': fields.Raw(description='Campaigns by type'),
    'topPerformingCampaigns': fields.List(fields.Raw, description='Top performing campaigns')
}

events_analytics_model = {
    'summary': fields.Raw(description='Analytics summary'),
    'eventsByType': fields.Raw(description='Events breakdown by type'),
    'eventsBySource': fields.Raw(description='Events breakdown by source'),
    'timeline': fields.Raw(description='Events timeline'),
    'topContacts': fields.List(fields.Raw, description='Most active contacts'),
    'generatedAt': fields.String(description='Analytics generation timestamp')
}

asset_statistics_model = {
    'summary': fields.Raw(description='Asset summary statistics'),
    'typeBreakdown': fields.List(fields.Raw, description='Assets by type'),
    'categoryBreakdown': fields.List(fields.Raw, description='Assets by category'),
    'recentAssets': fields.List(fields.Raw, description='Recently created assets'),
    'generatedAt': fields.String(description='Statistics generation timestamp')
}
