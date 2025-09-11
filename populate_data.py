import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta

from faker import Faker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.models import (
    Contact, Campaign, EmailDefinition, DataEvent, DataEventType, Asset,
    ContactStatus, CampaignStatus, EmailStatus, campaign_contacts, campaign_assets
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('populate_db.log')
    ]
)

logger = logging.getLogger(__name__)

fake = Faker(['pt_BR', 'en_US'])
Faker.seed(42)


def clear_database():
    logger.info("Limpando banco de dados")

    try:
        db.session.execute(campaign_assets.delete())
        db.session.execute(campaign_contacts.delete())
        DataEvent.query.delete()
        Asset.query.delete()
        Campaign.query.delete()
        EmailDefinition.query.delete()
        Contact.query.delete()

        db.session.commit()
        logger.info("Banco de dados limpo com sucesso")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao limpar banco: {e}")
        raise


def populate_contacts(count=500):
    """Cria contatos com dados fake"""
    logger.info(f"Criando {count} contatos")

    try:
        contacts = []

        for _ in range(count):
            birth_date = fake.date_of_birth(minimum_age=18, maximum_age=80)
            age = datetime.now().year - birth_date.year
            first_name = fake.first_name()
            last_name = fake.last_name()

            contact = Contact(
                email_address=fake.email(),
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}",
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
                    'interests': random.sample(['technology', 'sports', 'music', 'travel', 'food'],
                                               k=random.randint(1, 3)),
                    'purchase_history': random.randint(0, 50),
                    'lifetime_value': round(random.uniform(0, 5000), 2)
                })
            )
            contacts.append(contact)

        db.session.add_all(contacts)
        db.session.commit()

        logger.info(f"{len(contacts)} contatos criados com sucesso")
        return contacts

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar contatos: {e}")
        raise


def populate_email_definitions(count=100):
    """Cria definições de email"""
    logger.info(f"Criando {count} definições de email")

    try:
        email_definitions = []
        email_types = ['Triggered', 'Transactional', 'Marketing', 'Welcome', 'Abandoned Cart']

        for _ in range(count):
            subject = fake.sentence(nb_words=5)

            email_def = EmailDefinition(
                name=fake.sentence(nb_words=4),
                description=fake.text(max_nb_chars=150),
                subject=subject,
                html_content=f"<html><body><h1>{subject}</h1><p>{fake.paragraph()}</p></body></html>",
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

        db.session.add_all(email_definitions)
        db.session.commit()

        logger.info(f"{len(email_definitions)} definições de email criadas com sucesso")
        return email_definitions

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar definições de email: {e}")
        raise


def populate_campaigns(count=50, contacts=None, email_definitions=None):
    """Cria campanhas e associa com contatos e definições de email"""
    logger.info(f"Criando {count} campanhas")

    try:
        campaigns = []
        campaign_types = ['Email', 'SMS', 'Push Notification', 'Social Media']

        for _ in range(count):
            start_date = fake.date_time_between(start_date='-60d', end_date='+30d')
            end_date = start_date + timedelta(days=random.randint(1, 30))

            email_def = random.choice(email_definitions) if email_definitions else None

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
                email_definition_id=email_def.id if email_def else None,
                tags=json.dumps(random.sample(['promo', 'newsletter', 'announcement', 'seasonal', 'product-launch'],
                                              k=random.randint(1, 3)))
            )
            campaigns.append(campaign)

        db.session.add_all(campaigns)
        db.session.commit()

        if contacts:
            logger.info("Associando contatos às campanhas")
            for campaign in campaigns:
                num_contacts = random.randint(len(contacts) // 10, len(contacts) // 2)
                selected_contacts = random.sample(contacts, num_contacts)

                for contact in selected_contacts:
                    campaign.contacts.append(contact)

            db.session.commit()

        logger.info(f"{len(campaigns)} campanhas criadas com sucesso")
        return campaigns

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar campanhas: {e}")
        raise


def populate_data_events(count=2000, contacts=None, campaigns=None, email_definitions=None):
    """Cria eventos de dados com relacionamentos apropriados"""
    logger.info(f"Criando {count} eventos de dados")

    try:
        events = []
        sources = ['Email', 'Website', 'Mobile App', 'SMS', 'API']

        for _ in range(count):
            event_type = random.choice(list(DataEventType))

            contact = random.choice(contacts) if contacts else None
            campaign = random.choice(campaigns) if campaigns and random.random() > 0.3 else None
            email_def = random.choice(email_definitions) if email_definitions and random.random() > 0.5 else None

            if not contact:
                continue

            event_data = {}

            if event_type == DataEventType.EMAIL_OPEN:
                event_data = {
                    'userAgent': fake.user_agent(),
                    'ipAddress': fake.ipv4(),
                    'openDate': fake.date_time_between(start_date='-30d', end_date='now').isoformat()
                }
            elif event_type == DataEventType.EMAIL_CLICK:
                event_data = {
                    'url': fake.url(),
                    'linkName': fake.word(),
                    'userAgent': fake.user_agent(),
                    'ipAddress': fake.ipv4()
                }
            elif event_type == DataEventType.PURCHASE:
                event_data = {
                    'orderId': fake.uuid4(),
                    'amount': round(random.uniform(10, 500), 2),
                    'currency': 'BRL',
                    'products': [
                        {
                            'productId': fake.uuid4(),
                            'name': fake.catch_phrase(),
                            'price': round(random.uniform(10, 200), 2),
                            'quantity': random.randint(1, 3)
                        }
                        for _ in range(random.randint(1, 3))
                    ]
                }
            elif event_type == DataEventType.PAGE_VIEW:
                event_data = {
                    'url': fake.url(),
                    'pageTitle': fake.sentence(),
                    'sessionId': fake.uuid4(),
                    'timeOnPage': random.randint(10, 300)
                }
            elif event_type == DataEventType.FORM_SUBMISSION:
                event_data = {
                    'formId': fake.uuid4(),
                    'formName': " ".join(fake.words(nb=3)),
                    'fields': {
                        'name': fake.name(),
                        'email': fake.email(),
                        'message': fake.text(max_nb_chars=200)
                    }
                }

            event = DataEvent(
                event_type=event_type,
                contact_id=contact.id,
                campaign_id=campaign.id if campaign else None,
                email_definition_id=email_def.id if email_def else None,
                event_date=fake.date_time_between(start_date='-60d', end_date='now'),
                source=random.choice(sources),
                event_data=json.dumps(event_data) if event_data else None
            )

            events.append(event)

        batch_size = 100
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            db.session.add_all(batch)
            db.session.commit()
            logger.info(f"Inseridos {min(i + batch_size, len(events))}/{len(events)} eventos")

        logger.info(f"{len(events)} eventos de dados criados com sucesso")
        return events

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar eventos de dados: {e}")
        raise


def populate_assets(count=50, campaigns=None):
    """Cria assets e associa com campanhas"""
    logger.info(f"Criando {count} assets")

    try:
        assets = []
        asset_types = ['Image', 'Document', 'Template', 'Video', 'Audio']
        categories = ['Marketing', 'Templates', 'Logos', 'Product Images', 'Documents']

        for _ in range(count):
            asset_type = random.choice(asset_types)

            extensions = {
                'Image': ['jpg', 'png', 'gif', 'svg'],
                'Document': ['pdf', 'docx', 'txt'],
                'Template': ['html', 'htm'],
                'Video': ['mp4', 'avi'],
                'Audio': ['mp3', 'wav']
            }

            ext = random.choice(extensions[asset_type])
            filename = f"{fake.slug()}.{ext}"

            asset = Asset(
                name=fake.catch_phrase(),
                description=fake.text(max_nb_chars=150),
                asset_type=asset_type,
                file_name=filename,
                file_size=random.randint(1024, 5 * 1024 * 1024),
                mime_type=f"image/{ext}" if asset_type == 'Image' else f"application/{ext}",
                file_url=f"https://example.com/assets/{filename}",
                category=random.choice(categories),
                tags=json.dumps(
                    random.sample(['marketing', 'brand', 'campaign', 'social', 'web'], k=random.randint(1, 3)))
            )

            assets.append(asset)

        db.session.add_all(assets)
        db.session.commit()

        if campaigns:
            logger.info("Associando assets às campanhas")
            for asset in assets:
                num_campaigns = random.randint(0, min(3, len(campaigns)))
                if num_campaigns > 0:
                    selected_campaigns = random.sample(campaigns, num_campaigns)
                    for campaign in selected_campaigns:
                        asset.campaigns.append(campaign)

            db.session.commit()

        logger.info(f"{len(assets)} assets criados com sucesso")
        return assets

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar assets: {e}")
        raise


def generate_sample_queries():
    """Gera exemplos de consultas que aproveitam os relacionamentos"""
    logger.info("Exemplos de consultas com relacionamentos:")
    logger.info("=" * 50)

    contact = Contact.query.first()
    if contact:
        logger.info(f"1. Contato com relacionamentos:")
        logger.info(f"   Contato: {contact.email_address}")
        logger.info(f"   Total de eventos: {contact.data_events.count()}")
        logger.info(f"   Campanhas ativas: {len([c for c in contact.campaigns if c.status == CampaignStatus.RUNNING])}")

    campaign = Campaign.query.first()
    if campaign:
        logger.info(f"2. Campanha com estatísticas:")
        logger.info(f"   Campanha: {campaign.name}")
        logger.info(f"   Total enviado: {campaign.total_sent}")
        logger.info(f"   Total opens: {campaign.total_opens}")
        logger.info(
            f"   Taxa de abertura: {round(campaign.total_opens / campaign.total_sent * 100, 2) if campaign.total_sent > 0 else 0}%")

    # Contatos mais ativos
    logger.info("3. Consultas úteis:")
    logger.info("   # Contatos mais ativos:")
    logger.info(
        "   Contact.query.join(DataEvent).group_by(Contact.id).order_by(func.count(DataEvent.id).desc()).limit(10)")

    logger.info("   # Campanhas com melhor performance:")
    logger.info(
        "   Campaign.query.filter(Campaign.total_sent > 0).order_by((Campaign.total_opens / Campaign.total_sent).desc())")

    logger.info("   # Eventos de um tipo específico:")
    logger.info("   DataEvent.query.filter_by(event_type=DataEventType.EMAIL_OPEN).join(Contact).join(Campaign)")


def main():
    """Executa a população completa do banco com relacionamentos"""
    logger.info("Iniciando população do banco de dados da Marketing Cloud API")
    logger.info("Versão com relacionamentos apropriados")
    logger.info("=" * 60)

    with app.app_context():
        logger.info("Criando tabelas do banco de dados")
        db.create_all()
        clear_database()

        try:
            contacts = populate_contacts(5000)
            email_definitions = populate_email_definitions(1000)

            campaigns = populate_campaigns(500, contacts, email_definitions)

            events = populate_data_events(5000, contacts, campaigns, email_definitions)

            assets = populate_assets(500, campaigns)

            logger.info("População do banco concluída com relacionamentos")
            logger.info("=" * 40)
            logger.info(f"Contatos: {len(contacts)}")
            logger.info(f"Campanhas: {len(campaigns)}")
            logger.info(f"Definições de Email: {len(email_definitions)}")
            logger.info(f"Eventos de Dados: {len(events)}")
            logger.info(f"Assets: {len(assets)}")
            logger.info("=" * 40)

            generate_sample_queries()

            logger.info("API pronta para uso com relacionamentos apropriados")
            logger.info("Execute: python app.py")
            logger.info("Documentação: http://localhost:5000/v1")

        except Exception as e:
            logger.error(f"Erro durante a população: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
