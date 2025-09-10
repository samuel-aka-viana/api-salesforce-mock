import json
import os
import random
import sys

from faker import Faker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.models import (
    Contact, Campaign, EmailDefinition, DataEvent, DataEventType, Asset,
    populate_fake_contacts, populate_fake_campaigns, populate_fake_email_definitions
)

fake = Faker(['pt_BR', 'en_US'])
Faker.seed(42)


def clear_database():
    print("🗑️  Limpando banco de dados...")

    try:
        DataEvent.query.delete()
        Asset.query.delete()
        EmailDefinition.query.delete()
        Campaign.query.delete()
        Contact.query.delete()

        db.session.commit()
        print("✅ Banco de dados limpo com sucesso!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao limpar banco: {e}")
        raise


def populate_contacts(count=500):
    """Popular contatos usando a função do modelo"""
    print(f"👥 Criando {count} contatos...")

    try:
        created = populate_fake_contacts(count)
        print(f"✅ {created} contatos criados com sucesso!")
        return created
    except Exception as e:
        print(f"❌ Erro ao criar contatos: {e}")
        raise


def populate_campaigns(count=50):
    print(f"📧 Criando {count} campanhas...")

    try:
        created = populate_fake_campaigns(count)
        print(f"✅ {created} campanhas criadas com sucesso!")
        return created
    except Exception as e:
        print(f"❌ Erro ao criar campanhas: {e}")
        raise


def populate_email_definitions(count=100):
    """Popular definições de email usando a função do modelo"""
    print(f"📝 Criando {count} definições de email...")

    try:
        created = populate_fake_email_definitions(count)
        print(f"✅ {created} definições de email criadas com sucesso!")
        return created
    except Exception as e:
        print(f"❌ Erro ao criar definições de email: {e}")
        raise


def populate_data_events(count=2000):
    """Popular eventos de dados"""
    print(f"📊 Criando {count} eventos de dados...")

    try:
        # Buscar contatos existentes para associar eventos
        contacts = Contact.query.all()
        if not contacts:
            print("⚠️  Nenhum contato encontrado. Criando eventos sem contatos associados.")
            contact_keys = [f"contact_{i}" for i in range(100)]
        else:
            contact_keys = [c.contact_key for c in contacts]

        # Buscar campanhas e definições de email
        campaigns = Campaign.query.all()
        email_definitions = EmailDefinition.query.all()

        campaign_ids = [c.campaign_id for c in campaigns] if campaigns else [None]
        email_def_ids = [e.definition_id for e in email_definitions] if email_definitions else [None]

        events = []
        sources = ['Email', 'Website', 'Mobile App', 'SMS', 'API']

        for _ in range(count):
            # Gerar evento
            event_type = random.choice(list(DataEventType))
            contact_key = random.choice(contact_keys)

            # Dados específicos do evento baseado no tipo
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
                contact_key=contact_key,
                event_date=fake.date_time_between(start_date='-60d', end_date='now'),
                source=random.choice(sources),
                campaign_id=random.choice(campaign_ids) if random.random() > 0.3 else None,
                email_definition_id=random.choice(email_def_ids) if random.random() > 0.5 else None,
                event_data=json.dumps(event_data) if event_data else None
            )

            events.append(event)

        batch_size = 100
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            db.session.bulk_save_objects(batch)
            db.session.commit()
            print(f"📊 Inseridos {min(i + batch_size, len(events))}/{len(events)} eventos...")

        print(f"✅ {len(events)} eventos de dados criados com sucesso!")
        return len(events)

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar eventos de dados: {e}")
        raise


def populate_assets(count=50):
    """Popular assets (simulados - sem arquivos reais)"""
    print(f"🖼️  Criando {count} assets...")

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
                file_size=random.randint(1024, 5 * 1024 * 1024),  # 1KB to 5MB
                mime_type=f"image/{ext}" if asset_type == 'Image' else f"application/{ext}",
                file_url=f"https://example.com/assets/{filename}",
                category=random.choice(categories),
                tags=json.dumps(
                    random.sample(['marketing', 'brand', 'campaign', 'social', 'web'], k=random.randint(1, 3)))
            )

            assets.append(asset)

        db.session.bulk_save_objects(assets)
        db.session.commit()

        print(f"✅ {len(assets)} assets criados com sucesso!")
        return len(assets)

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar assets: {e}")
        raise


def update_campaign_statistics():
    """Atualizar estatísticas das campanhas baseado nos eventos"""
    print("📈 Atualizando estatísticas das campanhas...")

    try:
        campaigns = Campaign.query.all()

        for campaign in campaigns:
            campaign_events = DataEvent.query.filter_by(campaign_id=campaign.campaign_id).all()

            opens = sum(1 for e in campaign_events if e.event_type == DataEventType.EMAIL_OPEN)
            clicks = sum(1 for e in campaign_events if e.event_type == DataEventType.EMAIL_CLICK)
            bounces = sum(1 for e in campaign_events if e.event_type == DataEventType.EMAIL_BOUNCE)
            unsubscribes = sum(1 for e in campaign_events if e.event_type == DataEventType.EMAIL_UNSUBSCRIBE)

            if not campaign_events and campaign.total_sent == 0:
                campaign.total_sent = random.randint(100, 5000)

            campaign.total_opens = opens
            campaign.total_clicks = clicks
            campaign.total_bounces = bounces
            campaign.total_unsubscribes = unsubscribes

        db.session.commit()
        print("✅ Estatísticas das campanhas atualizadas!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao atualizar estatísticas: {e}")
        raise


def generate_sample_api_calls():
    """Gerar exemplos de chamadas da API"""
    print("\n🔧 Exemplos de uso da API:")
    print("=" * 50)

    contact = Contact.query.first()
    campaign = Campaign.query.first()
    email_def = EmailDefinition.query.first()

    print("\n1. Autenticação:")
    print("POST /v1/auth/token")
    print(json.dumps({
        "client_id": "marketing_cloud_app_1",
        "client_secret": "super_secret_key_123",
        "grant_type": "client_credentials"
    }, indent=2))

    if contact:
        print(f"\n2. Buscar contato específico:")
        print(f"GET /contacts/v1/contacts/{contact.contact_key}")
        print("Headers: Authorization: Bearer <token>")

    print("\n3. Listar campanhas:")
    print("GET /campaigns/v1/campaigns?page=1&per_page=10&status=Running")
    print("Headers: Authorization: Bearer <token>")

    if email_def:
        print(f"\n4. Enviar email:")
        print(f"POST /email/v1/definitions/{email_def.definition_key}/send")
        print("Headers: Authorization: Bearer <token>")
        print(json.dumps({
            "recipients": [
                {
                    "email": "teste@example.com",
                    "firstName": "João",
                    "lastName": "Silva"
                }
            ]
        }, indent=2))

    print("\n5. Criar evento de dados:")
    print("POST /data/v1/events")
    print("Headers: Authorization: Bearer <token>")
    print(json.dumps({
        "eventType": "EmailOpen",
        "contactKey": contact.contact_key if contact else "example_contact",
        "eventData": {
            "userAgent": "Mozilla/5.0...",
            "ipAddress": "192.168.1.1"
        }
    }, indent=2))


def main():
    """Função principal"""
    print("🚀 Iniciando população do banco de dados da Marketing Cloud API")
    print("=" * 60)

    # Verificar se deve limpar o banco
    clear_db = input("🤔 Limpar banco de dados existente? (s/N): ").lower().strip()

    with app.app_context():
        # Criar tabelas se não existirem
        print("🛠️  Criando tabelas do banco de dados...")
        db.create_all()

        if clear_db == 's':
            clear_database()

        try:
            # Popular dados
            contact_count = populate_contacts(500)
            campaign_count = populate_campaigns(50)
            email_def_count = populate_email_definitions(100)
            event_count = populate_data_events(2000)
            asset_count = populate_assets(50)

            # Atualizar estatísticas
            update_campaign_statistics()

            # Resumo
            print("\n🎉 População do banco concluída!")
            print("=" * 40)
            print(f"👥 Contatos: {contact_count}")
            print(f"📧 Campanhas: {campaign_count}")
            print(f"📝 Definições de Email: {email_def_count}")
            print(f"📊 Eventos de Dados: {event_count}")
            print(f"🖼️  Assets: {asset_count}")
            print("=" * 40)

            # Gerar exemplos de API
            generate_sample_api_calls()

            print(f"\n✨ API pronta para uso!")
            print(f"🌐 Execute: python app.py")
            print(f"📖 Documentação: http://localhost:5000/v1")

        except Exception as e:
            print(f"\n💥 Erro durante a população: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
