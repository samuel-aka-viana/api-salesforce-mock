import json
import uuid
from datetime import datetime
from enum import Enum

from faker import Faker
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
fake = Faker(['pt_BR', 'en_US'])


class ContactStatus(Enum):
    ACTIVE = "Active"
    UNSUBSCRIBED = "Unsubscribed"
    BOUNCED = "Bounced"
    HELD = "Held"


class CampaignStatus(Enum):
    DRAFT = "Draft"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class EmailStatus(Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    ARCHIVED = "Archived"


class DataEventType(Enum):
    EMAIL_OPEN = "EmailOpen"
    EMAIL_CLICK = "EmailClick"
    EMAIL_BOUNCE = "EmailBounce"
    EMAIL_UNSUBSCRIBE = "EmailUnsubscribe"
    PURCHASE = "Purchase"
    PAGE_VIEW = "PageView"
    FORM_SUBMISSION = "FormSubmission"


campaign_contacts = db.Table('campaign_contacts',
                             db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id'), primary_key=True),
                             db.Column('contact_id', db.Integer, db.ForeignKey('contacts.id'), primary_key=True),
                             db.Column('sent_date', db.DateTime, default=datetime.utcnow),
                             db.Column('status', db.String(50), default='Sent')
                             )


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    contact_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    contact_id = db.Column(db.String(100), unique=True, nullable=False)

    email_address = db.Column(db.String(255), nullable=False, index=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    full_name = db.Column(db.String(200))

    gender = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    age = db.Column(db.Integer)

    street_address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50))

    phone_number = db.Column(db.String(50))
    mobile_number = db.Column(db.String(50))

    status = db.Column(db.Enum(ContactStatus), default=ContactStatus.ACTIVE)
    html_enabled = db.Column(db.Boolean, default=True)
    email_opt_in = db.Column(db.Boolean, default=True)
    sms_opt_in = db.Column(db.Boolean, default=False)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_date = db.Column(db.DateTime)

    custom_attributes = db.Column(db.Text)

    data_events = db.relationship('DataEvent', backref='contact', lazy='dynamic', cascade='all, delete-orphan')
    campaigns = db.relationship('Campaign', secondary=campaign_contacts, back_populates='contacts')

    def __init__(self, **kwargs):
        super(Contact, self).__init__(**kwargs)
        if not self.contact_key:
            self.contact_key = str(uuid.uuid4())
        if not self.contact_id:
            self.contact_id = str(uuid.uuid4())

    def to_dict(self, include_relationships=False):
        """Converte o modelo para dicionário"""
        custom_attrs = {}
        if self.custom_attributes:
            try:
                custom_attrs = json.loads(self.custom_attributes)
            except:
                pass

        result = {
            'contactKey': self.contact_key,
            'contactId': self.contact_id,
            'emailAddress': self.email_address,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'fullName': self.full_name,
            'gender': self.gender,
            'birthDate': self.birth_date.isoformat() if self.birth_date else None,
            'age': self.age,
            'streetAddress': self.street_address,
            'city': self.city,
            'state': self.state,
            'postalCode': self.postal_code,
            'country': self.country,
            'phoneNumber': self.phone_number,
            'mobileNumber': self.mobile_number,
            'status': self.status.value if self.status else None,
            'htmlEnabled': self.html_enabled,
            'emailOptIn': self.email_opt_in,
            'smsOptIn': self.sms_opt_in,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'modifiedDate': self.modified_date.isoformat() if self.modified_date else None,
            'lastActivityDate': self.last_activity_date.isoformat() if self.last_activity_date else None,
            'customAttributes': custom_attrs
        }

        if include_relationships:
            result['totalEvents'] = self.data_events.count()
            result['activeCampaigns'] = len([c for c in self.campaigns if c.status == CampaignStatus.RUNNING])

        return result


class EmailDefinition(db.Model):
    __tablename__ = 'email_definitions'

    id = db.Column(db.Integer, primary_key=True)
    definition_key = db.Column(db.String(100), unique=True, nullable=False)
    definition_id = db.Column(db.String(100), unique=True, nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(255))

    html_content = db.Column(db.Text)
    text_content = db.Column(db.Text)

    status = db.Column(db.Enum(EmailStatus), default=EmailStatus.DRAFT)
    email_type = db.Column(db.String(50))

    from_name = db.Column(db.String(100))
    from_email = db.Column(db.String(255))
    reply_to_email = db.Column(db.String(255))

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    track_opens = db.Column(db.Boolean, default=True)
    track_clicks = db.Column(db.Boolean, default=True)

    campaigns = db.relationship('Campaign', backref='email_definition', lazy='dynamic')
    data_events = db.relationship('DataEvent', backref='email_definition', lazy='dynamic')

    def __init__(self, **kwargs):
        super(EmailDefinition, self).__init__(**kwargs)
        if not self.definition_key:
            self.definition_key = str(uuid.uuid4())
        if not self.definition_id:
            self.definition_id = str(uuid.uuid4())

    def to_dict(self, include_relationships=False):
        result = {
            'definitionKey': self.definition_key,
            'definitionId': self.definition_id,
            'name': self.name,
            'description': self.description,
            'subject': self.subject,
            'htmlContent': self.html_content,
            'textContent': self.text_content,
            'status': self.status.value if self.status else None,
            'emailType': self.email_type,
            'fromName': self.from_name,
            'fromEmail': self.from_email,
            'replyToEmail': self.reply_to_email,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'modifiedDate': self.modified_date.isoformat() if self.modified_date else None,
            'trackOpens': self.track_opens,
            'trackClicks': self.track_clicks
        }

        if include_relationships:
            result['campaignCount'] = self.campaigns.count()
            result['totalEvents'] = self.data_events.count()

        return result


class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.String(100), unique=True, nullable=False)
    campaign_key = db.Column(db.String(100), unique=True, nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    campaign_type = db.Column(db.String(50))

    status = db.Column(db.Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)

    subject_line = db.Column(db.String(255))
    from_name = db.Column(db.String(100))
    from_email = db.Column(db.String(255))
    reply_to_email = db.Column(db.String(255))

    email_definition_id = db.Column(db.Integer, db.ForeignKey('email_definitions.id'), nullable=True)

    contacts = db.relationship('Contact', secondary=campaign_contacts, back_populates='campaigns')
    data_events = db.relationship('DataEvent', backref='campaign', lazy='dynamic')

    tags = db.Column(db.Text)

    def __init__(self, **kwargs):
        super(Campaign, self).__init__(**kwargs)
        if not self.campaign_id:
            self.campaign_id = str(uuid.uuid4())
        if not self.campaign_key:
            self.campaign_key = str(uuid.uuid4())

    @property
    def total_sent(self):
        return len(self.contacts)

    @property
    def total_opens(self):
        return self.data_events.filter_by(event_type=DataEventType.EMAIL_OPEN).count()

    @property
    def total_clicks(self):
        return self.data_events.filter_by(event_type=DataEventType.EMAIL_CLICK).count()

    @property
    def total_bounces(self):
        return self.data_events.filter_by(event_type=DataEventType.EMAIL_BOUNCE).count()

    @property
    def total_unsubscribes(self):
        return self.data_events.filter_by(event_type=DataEventType.EMAIL_UNSUBSCRIBE).count()

    def to_dict(self, include_relationships=False):
        tags_list = []
        if self.tags:
            try:
                tags_list = json.loads(self.tags)
            except:
                pass

        result = {
            'campaignId': self.campaign_id,
            'campaignKey': self.campaign_key,
            'name': self.name,
            'description': self.description,
            'campaignType': self.campaign_type,
            'status': self.status.value if self.status else None,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'modifiedDate': self.modified_date.isoformat() if self.modified_date else None,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'subjectLine': self.subject_line,
            'fromName': self.from_name,
            'fromEmail': self.from_email,
            'replyToEmail': self.reply_to_email,
            'emailDefinitionId': self.email_definition_id,
            'statistics': {
                'totalSent': self.total_sent,
                'totalOpens': self.total_opens,
                'totalClicks': self.total_clicks,
                'totalBounces': self.total_bounces,
                'totalUnsubscribes': self.total_unsubscribes,
                'openRate': round((self.total_opens / self.total_sent * 100), 2) if self.total_sent > 0 else 0,
                'clickRate': round((self.total_clicks / self.total_sent * 100), 2) if self.total_sent > 0 else 0,
                'bounceRate': round((self.total_bounces / self.total_sent * 100), 2) if self.total_sent > 0 else 0
            },
            'tags': tags_list
        }

        if include_relationships:
            result['contactCount'] = len(self.contacts)
            result['emailDefinition'] = self.email_definition.to_dict() if self.email_definition else None

        return result


class DataEvent(db.Model):
    __tablename__ = 'data_events'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), unique=True, nullable=False)

    event_type = db.Column(db.Enum(DataEventType), nullable=False)
    event_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    event_data = db.Column(db.Text)
    source = db.Column(db.String(100))

    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    email_definition_id = db.Column(db.Integer, db.ForeignKey('email_definitions.id'), nullable=True, index=True)

    @property
    def contact_key(self):
        return self.contact.contact_key if self.contact else None
    def __init__(self, **kwargs):
        super(DataEvent, self).__init__(**kwargs)
        if not self.event_id:
            self.event_id = str(uuid.uuid4())

    def to_dict(self, include_relationships=False):
        event_data = {}
        if self.event_data:
            try:
                event_data = json.loads(self.event_data)
            except:
                pass

        result = {
            'eventId': self.event_id,
            'eventType': self.event_type.value if self.event_type else None,
            'eventDate': self.event_date.isoformat() if self.event_date else None,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'eventData': event_data,
            'source': self.source,
            'contactId': self.contact_id,
            'campaignId': self.campaign_id,
            'emailDefinitionId': self.email_definition_id
        }

        if include_relationships:
            result['contact'] = self.contact.to_dict() if self.contact else None
            result['campaign'] = self.campaign.to_dict() if self.campaign else None
            result['emailDefinition'] = self.email_definition.to_dict() if self.email_definition else None

        return result


class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(100), unique=True, nullable=False)
    asset_key = db.Column(db.String(100), unique=True, nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    asset_type = db.Column(db.String(50))

    file_name = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    file_url = db.Column(db.String(500))

    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags = db.Column(db.Text)
    category = db.Column(db.String(100))

    campaigns = db.relationship('Campaign', secondary='campaign_assets', backref='assets')

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        if not self.asset_id:
            self.asset_id = str(uuid.uuid4())
        if not self.asset_key:
            self.asset_key = str(uuid.uuid4())

    def to_dict(self, include_relationships=False):
        tags_list = []
        if self.tags:
            try:
                tags_list = json.loads(self.tags)
            except:
                pass

        result = {
            'assetId': self.asset_id,
            'assetKey': self.asset_key,
            'name': self.name,
            'description': self.description,
            'assetType': self.asset_type,
            'fileName': self.file_name,
            'fileSize': self.file_size,
            'mimeType': self.mime_type,
            'fileUrl': self.file_url,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'modifiedDate': self.modified_date.isoformat() if self.modified_date else None,
            'tags': tags_list,
            'category': self.category
        }

        if include_relationships:
            result['usedInCampaigns'] = len(self.campaigns)

        return result


campaign_assets = db.Table('campaign_assets',
                           db.Column('campaign_id', db.Integer, db.ForeignKey('campaigns.id'), primary_key=True),
                           db.Column('asset_id', db.Integer, db.ForeignKey('assets.id'), primary_key=True),
                           db.Column('usage_type', db.String(50), default='content'),
                           db.Column('created_date', db.DateTime, default=datetime.utcnow)
                           )


class ContactService:
    @staticmethod
    def get_contact_activity_summary(contact_id):
        contact = Contact.query.get(contact_id)
        if not contact:
            return None

        events = contact.data_events.all()
        campaigns = contact.campaigns

        return {
            'contact': contact.to_dict(),
            'totalEvents': len(events),
            'eventsByType': {
                event_type.value: len([e for e in events if e.event_type == event_type])
                for event_type in DataEventType
            },
            'activeCampaigns': len([c for c in campaigns if c.status == CampaignStatus.RUNNING]),
            'totalCampaigns': len(campaigns),
            'lastActivityDate': max([e.event_date for e in events]) if events else None
        }

    @staticmethod
    def get_campaign_performance(campaign_id):
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return None

        events = campaign.data_events.all()

        return {
            'campaign': campaign.to_dict(include_relationships=True),
            'events': [e.to_dict() for e in events],
            'performance': {
                'deliveryRate': round((campaign.total_sent - campaign.total_bounces) / campaign.total_sent * 100,
                                      2) if campaign.total_sent > 0 else 0,
                'engagementRate': round((campaign.total_opens + campaign.total_clicks) / campaign.total_sent * 100,
                                        2) if campaign.total_sent > 0 else 0,
                'unsubscribeRate': round(campaign.total_unsubscribes / campaign.total_sent * 100,
                                         2) if campaign.total_sent > 0 else 0
            }
        }
