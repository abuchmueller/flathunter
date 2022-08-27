""" Startup file for Google Cloud deployment or local webserver"""
import logging

from flathunter.idmaintainer import IdMaintainer
from flathunter.googlecloud_idmaintainer import GoogleCloudIdMaintainer
from flathunter.web_hunter import WebHunter
from flathunter.config import Config
from flathunter.logging import logger, wdm_logger

from flathunter.web import app

config = Config()

if __name__ == '__main__':
    # Use the SQLite DB file if we are running locally
    id_watch = IdMaintainer(f'{config.database_location()}/processed_ids.db')
else:
    # Use Google Cloud DB if we run on the cloud
    id_watch = GoogleCloudIdMaintainer()

# adjust log level, if required
if config.get('verbose'):
    logger.setLevel(logging.DEBUG)
    # Allow logging of "webdriver-manager" module on verbose mode
    wdm_logger.setLevel(logging.INFO)

# initialize search plugins for config
config.init_searchers()

hunter = WebHunter(config, id_watch)

app.config["HUNTER"] = hunter
if 'website' in config:
    app.secret_key = config['website']['session_key']
    app.config["DOMAIN"] = config['website']['domain']
    app.config["BOT_NAME"] = config['website']['bot_name']
else:
    app.secret_key = b'Not a secret'
notifiers = config.get("notifiers", [])
if "telegram" in notifiers:
    app.config["BOT_TOKEN"] = config['telegram']['bot_token']
if "mattermost" in notifiers:
    app.config["MM_WEBHOOK_URL"] = config['mattermost']['webhook_url']

if __name__ == '__main__':
    listen = config['website'].get('listen', {})
    host = listen.get('host', '127.0.0.1')
    port = listen.get('port', '8080')
    app.run(host=host, port=port, debug=True)
