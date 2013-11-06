"""Superdesk IO"""

import superdesk
from superdesk.utc import utcnow

providers = {}

def register_provider(type, provider):
    providers[type] = provider

superdesk.provider = register_provider

def update_provider(provider):
    """Update given provider."""

    if provider.get('type') in providers:
        start = utcnow()
        ingested_count = provider.get('ingested_count', 0)
        for item in providers[provider.get('type')].update(provider):
            item.setdefault('created', utcnow())
            item.setdefault('updated', utcnow())
            item['ingest_provider'] = str(provider['_id'])

            old_item = superdesk.app.data.find_one('items', guid=item['guid'])
            if old_item:
                superdesk.app.data.update('items', str(old_item.get('_id')), item)
            else:
                ingested_count += 1
                superdesk.app.data.insert('items', [item])

        superdesk.app.data.update('ingest_providers', str(provider.get('_id')), {
            'updated': start,
            'ingested_count': ingested_count
        })

class UpdateIngest(superdesk.Command):
    """Update ingest providers."""

    option_list = (
        superdesk.Option('--provider', '-p', dest='provider_type'),
    )

    def run(self, provider_type=None):
        for provider in superdesk.app.data.find_all('ingest_providers'):
            if not provider_type or provider_type == provider.get('type'):
                update_provider(provider)

class AddProvider(superdesk.Command):
    """Add ingest provider."""

    option_list = {
        superdesk.Option('--provider', '-p', dest='provider'),
    }

    def run(self, provider=None):
        if provider:
            data = superdesk.json.loads(provider)
            data.setdefault('created', utcnow())
            data.setdefault('updated', utcnow())
            data.setdefault('name', data['type'])
            db = superdesk.get_db()
            db['ingest_providers'].save(data)
            return data

superdesk.command('ingest:update', UpdateIngest())
superdesk.command('ingest:provider', AddProvider())

superdesk.domain('feeds', {
    'schema': {
        'provider': {
            'type': 'string'
        }
    }
})

# load providers now to have available types for the schema
import superdesk.io.reuters
import superdesk.io.aap

schema = {
    'name': {
        'type': 'string',
        'required': True
    },
    'type': {
        'type': 'string',
        'required': True,
        'allowed': providers.keys()
    },
    'config': {
        'type': 'dict'
    },
    'ingested_count': {
        'type': 'integer',
        'readonly': True
    },
    'accepted_count': {
        'type': 'integer',
        'readonly': True
    }
}

superdesk.domain('ingest_providers', {
    'schema': schema
})
