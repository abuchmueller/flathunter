"""Functions and classes related to sending Telegram messages"""
import urllib.request
import urllib.parse
import urllib.error
import requests

from flathunter.logging import logger
from flathunter.abstract_processor import Processor
from flathunter.exceptions import BotBlockedException, UserDeactivatedException

class SenderTelegram(Processor):
    """Expose processor that sends Telegram messages"""

    def __init__(self, config, receivers=None):
        self.config = config
        self.bot_token = self.config.get('telegram', {}).get('bot_token', '')
        if receivers is None:
            self.receiver_ids = self.config.get('telegram', {}).get('receiver_ids', [])
        else:
            self.receiver_ids = receivers

    def process_expose(self, expose):
        """Send a message to a user describing the expose"""
        message = self.config.get('message', "").format(
            title=expose['title'],
            rooms=expose['rooms'],
            size=expose['size'],
            price=expose['price'],
            url=expose['url'],
            address=expose['address'],
            durations="" if 'durations' not in expose else expose['durations']).strip()
        self.send_msg(message)
        return expose

    def send_msg(self, message):
        """Send messages to each of the receivers in receiver_ids"""
        if self.receiver_ids is None:
            return
        for chat_id in self.receiver_ids:
            url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%i&text=%s'
            text = urllib.parse.quote_plus(message.encode('utf-8'))
            logger.debug(('token:', self.bot_token))
            logger.debug(('chatid:', chat_id))
            logger.debug(('text', text))
            qry = url % (self.bot_token, chat_id, text)
            logger.debug("Retrieving URL %s", qry)
            resp = requests.get(qry)
            logger.debug("Got response (%i): %s", resp.status_code, resp.content)
            data = resp.json()

            # handle error
            if resp.status_code != 200:
                status_code = resp.status_code
                logger.error("When sending bot message, we got status %i with message: %s",
                                   status_code, data)
                if resp.status_code == 403:
                    if "description" in data:
                        if "bot was blocked by the user" in data["description"]:
                            raise BotBlockedException("User %i blocked the bot" % chat_id)
                        if "user is deactivated" in data["description"]:
                            raise UserDeactivatedException("User %i has been deactivated" % chat_id)
