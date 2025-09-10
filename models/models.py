"""
Modelos de dados para Marketing Cloud API
Utiliza SQLAlchemy e Faker para gerar dados simulados
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from faker import Faker
import json
import uuid
import random
from enum import Enum

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

    def __init__(self, **kwargs):
        super(Contact, self).__init__(**kwargs)
        if not self.contact_key:
            self.contact_key = str(uuid.uuid4())
        if not self.contact_id:
            self.contact_id = str(uuid.uuid4())

    def to_dict(self):
        """Converte o modelo para dicionário"""
        custom_attrs = {}
        if self.custom_attributes:
            try:
                custom_attrs = json.loads(self.custom_attributes)
            except:
                pass

        return {
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

    total_sent = db.Column(db.Integer, default=0)
    total_opens = db.Column(db.Integer, default=0)
    total_clicks = db.Column(db.Integer, default=0)
    total_bounces = db.Column(db.Integer, default=0)
    total_unsubscribes = db.Column(db.Integer, default=0)

    tags = db.Column(db.Text)

    def __init__(self, **kwargs):
        super(Campaign, self).__init__(**kwargs)
        if not self.campaign_id:
            self.campaign_id = str(uuid.uuid4())
        if not self.campaign_key:
            self.campaign_key = str(uuid.uuid4())

    def to_dict(self):
        tags_list = []
        if self.tags:
            try:
                tags_list = json.loads(self.tags)
            except:
                pass

        return {
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

    def __init__(self, **kwargs):
        super(EmailDefinition, self).__init__(**kwargs)
        if not self.definition_key:
            self.definition_key = str(uuid.uuid4())
        if not self.definition_id:
            self.definition_id = str(uuid.uuid4())

    def to_dict(self):
        return {
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


class DataEvent(db.Model):
    __tablename__ = 'data_events'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), unique=True, nullable=False)

    event_type = db.Column(db.Enum(DataEventType), nullable=False)
    contact_key = db.Column(db.String(100), nullable=False, index=True)

    event_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    event_data = db.Column(db.Text)
    source = db.Column(db.String(100))
    campaign_id = db.Column(db.String(100))
    email_definition_id = db.Column(db.String(100))

    def __init__(self, **kwargs):
        super(DataEvent, self).__init__(**kwargs)
        if not self.event_id:
            self.event_id = str(uuid.uuid4())

    def to_dict(self):
        event_data = {}
        if self.event_data:
            try:
                event_data = json.loads(self.event_data)
            except:
                pass

        return {
            'eventId': self.event_id,
            'eventType': self.event_type.value if self.event_type else None,
            'contactKey': self.contact_key,
            'eventDate': self.event_date.isoformat() if self.event_date else None,
            'createdDate': self.created_date.isoformat() if self.created_date else None,
            'eventData': event_data,
            'source': self.source,
            'campaignId': self.campaign_id,
            'emailDefinitionId': self.email_definition_id
        }


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

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        if not self.asset_id:
            self.asset_id = str(uuid.uuid4())
        if not self.asset_key:
            self.asset_key = str(uuid.uuid4())

    def to_dict(self):
        tags_list = []
        if self.tags:
            try:
                tags_list = json.loads(self.tags)
            except:
                pass

        return {
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


def populate_fake_contacts(count=100):
    """Popula o banco com contatos fake"""
    contacts = []

    for _ in range(count):
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=80)
        age = datetime.now().year - birth_date.year

        contact = Contact(
            email_address=fake.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            gender=random.choice(['Male', 'Female', 'Other']),
            birth_date=birth_date,
            age=age,
            street_address=fake.street_address(),
            city=fake.city(),
            state=fake.state(),
            postal_code=fake.postcode(),
            country='Brazil',
            phone_number=fake.phone_number(),
            mobile_number=fake.phone_number(),
            status=random.choice(list(ContactStatus)),
            html_enabled=random.choice([True, False]),
            email_opt_in=random.choice([True, True, True, False]),  # 75% opt-in
            sms_opt_in=random.choice([True, False, False, False]),  # 25% opt-in
            last_activity_date=fake.date_time_between(start_date='-30d', end_date='now'),
            custom_attributes=json.dumps({
                'segment': random.choice(['VIP', 'Premium', 'Regular', 'New']),
                'interests': random.sample(['technology', 'sports', 'music', 'travel', 'food'], k=random.randint(1, 3)),
                'purchase_history': random.randint(0, 50),
                'lifetime_value': round(random.uniform(0, 5000), 2)
            })
        )
        contact.full_name = f"{contact.first_name} {contact.last_name}"
        contacts.append(contact)

    db.session.bulk_save_objects(contacts)
    db.session.commit()
    return len(contacts)


def populate_fake_campaigns(count=20):
    """Popula o banco com campanhas fake"""
    campaigns = []

    campaign_types = ['Email', 'SMS', 'Push Notification', 'Social Media']

    for _ in range(count):
        start_date = fake.date_time_between(start_date='-60d', end_date='+30d')
        end_date = start_date + timedelta(days=random.randint(1, 30))

        total_sent = random.randint(100, 10000)
        total_opens = int(total_sent * random.uniform(0.15, 0.45))  # 15-45% open rate
        total_clicks = int(total_opens * random.uniform(0.05, 0.25))  # 5-25% click rate
        total_bounces = int(total_sent * random.uniform(0.01, 0.05))  # 1-5% bounce rate
        total_unsubscribes = int(total_sent * random.uniform(0.001, 0.01))  # 0.1-1% unsubscribe rate

        campaign = Campaign(
            name=fake.catch_phrase(),
            description=fake.text(max_nb_chars=200),
            campaign_type=random.choice(campaign_types),
            status=random.choice(list(CampaignStatus)),
            start_date=start_date,
            end_date=end_date,
            subject_line=fake.sentence(nb_words=6),
            from_name=fake.company(),
            from_email=fake.company_email(),
            reply_to_email=fake.company_email(),
            total_sent=total_sent,
            total_opens=total_opens,
            total_clicks=total_clicks,
            total_bounces=total_bounces,
            total_unsubscribes=total_unsubscribes,
            tags=json.dumps(random.sample(['promo', 'newsletter', 'announcement', 'seasonal', 'product-launch'],
                                          k=random.randint(1, 3)))
        )
        campaigns.append(campaign)

    db.session.bulk_save_objects(campaigns)
    db.session.commit()
    return len(campaigns)


def populate_fake_email_definitions(count=30):
    """Popula o banco com definições de email fake"""
    email_definitions = []

    email_types = ['Triggered', 'Transactional', 'Marketing', 'Welcome', 'Abandoned Cart']

    for _ in range(count):
        email_def = EmailDefinition(
            name=fake.sentence(nb_words=4),
            description=fake.text(max_nb_chars=150),
            subject=fake.sentence(nb_words=5),
            html_content=f"<html><body><h1>{fake.sentence()}</h1><p>{fake.paragraph()}</p></body></html>",
            text_content=fake.paragraph(),
            status=random.choice(list(EmailStatus)),
            email_type=random.choice(email_types),
            from_name=fake.company(),
            from_email=fake.company_email(),
            reply_to_email=fake.company_email(),
            track_opens=random.choice([True, False]),
            track_clicks=random.choice([True, False])
        )
        email_definitions.append(email_def)

    db.session.bulk_save_objects(email_definitions)
    db.session.commit()
    return len(email_definitions)