"""Wrap configuration options as an object"""
import os
from typing import Optional

import yaml
from dotenv import load_dotenv

from flathunter.captcha.captcha_solver import CaptchaSolver
from flathunter.captcha.imagetyperz_solver import ImageTyperzSolver
from flathunter.captcha.twocaptcha_solver import TwoCaptchaSolver
from flathunter.crawl_ebaykleinanzeigen import CrawlEbayKleinanzeigen
from flathunter.crawl_idealista import CrawlIdealista
from flathunter.crawl_immobiliare import CrawlImmobiliare
from flathunter.crawl_immobilienscout import CrawlImmobilienscout
from flathunter.crawl_immowelt import CrawlImmowelt
from flathunter.crawl_wggesucht import CrawlWgGesucht
from flathunter.crawler_subito import CrawlSubito
from flathunter.filter import Filter
from flathunter.logging import logger

load_dotenv()


def _read_env(key, fallback=None):
    """ read the given key from environment"""
    return os.environ.get(key, fallback)


class Env:
    # Captcha setup
    FLATHUNTER_2CAPTCHA_KEY = _read_env("FLATHUNTER_2CAPTCHA_KEY")
    FLATHUNTER_IMAGETYPERZ_TOKEN = _read_env("FLATHUNTER_IMAGETYPERZ_TOKEN")
    FLATHUNTER_HEADLESS_BROWSER = _read_env("FLATHUNTER_HEADLESS_BROWSER")

    # Generic Config
    FLATHUNTER_TARGET_URLS = _read_env("FLATHUNTER_TARGET_URLS")
    FLATHUNTER_DATABASE_LOCATION = _read_env("FLATHUNTER_DATABASE_LOCATION")
    FLATHUNTER_GOOGLE_CLOUD_PROJECT_ID = _read_env("FLATHUNTER_GOOGLE_CLOUD_PROJECT_ID")
    FLATHUNTER_VERBOSE_LOG = _read_env("FLATHUNTER_VERBOSE_LOG")
    FLATHUNTER_LOOP_PERIOD_SECONDS = _read_env("FLATHUNTER_LOOP_PERIOD_SECONDS")
    FLATHUNTER_MESSAGE_FORMAT = _read_env("FLATHUNTER_MESSAGE_FORMAT")

    # Website setup
    FLATHUNTER_WEBSITE_SESSION_KEY = _read_env("FLATHUNTER_WEBSITE_SESSION_KEY")
    FLATHUNTER_WEBSITE_DOMAIN = _read_env("FLATHUNTER_WEBSITE_DOMAIN")
    FLATHUNTER_WEBSITE_BOT_NAME = _read_env("FLATHUNTER_WEBSITE_BOT_NAME")

    # Notification setup
    FLATHUNTER_NOTIFIERS = _read_env("FLATHUNTER_NOTIFIERS")
    FLATHUNTER_TELEGRAM_BOT_TOKEN = _read_env("FLATHUNTER_TELEGRAM_BOT_TOKEN")
    FLATHUNTER_TELEGRAM_BOT_NOTIFY_WITH_IMAGES = _read_env("FLATHUNTER_TELEGRAM_BOT_NOTIFY_WITH_IMAGES")
    FLATHUNTER_TELEGRAM_RECEIVER_IDS = _read_env("FLATHUNTER_TELEGRAM_RECEIVER_IDS")
    FLATHUNTER_MATTERMOST_WEBHOOK_URL = _read_env("FLATHUNTER_MATTERMOST_WEBHOOK_URL")


class Config:
    """Class to represent flathunter configuration"""

    DEFAULT_MESSAGE_FORMAT = """{title}
Zimmer: {rooms}
Größe: {size}
Preis: {price}

{url}"""

    def __init__(self, filename=None, string=None):
        self.useEnvironment = True
        if string is not None:
            self.config = yaml.safe_load(string)
            self.useEnvironment = False
        else:
            if filename is None and Env.FLATHUNTER_TARGET_URLS is None:
                raise Exception("Config file loaction must be specified, or FLATHUNTER_TARGET_URLS must be set")
            if filename is not None:
                logger.info("Using config path %s", filename)
                if not os.path.exists(filename):
                    raise Exception("No config file found at location %s")
                with open(filename, encoding="utf-8") as file:
                    self.config = yaml.safe_load(file)
            else:
                self.config = {}
        self.__searchers__ = []
        self.check_deprecated()

    def __iter__(self):
        """Emulate dictionary"""
        return self.config.__iter__()

    def __getitem__(self, value):
        """Emulate dictionary"""
        return self.config[value]

    def init_searchers(self):
        """Initialize search plugins"""
        self.__searchers__ = [
            CrawlImmobilienscout(self),
            CrawlWgGesucht(self),
            CrawlEbayKleinanzeigen(self),
            CrawlImmowelt(self),
            CrawlSubito(self),
            CrawlImmobiliare(self),
            CrawlIdealista(self)
        ]

    def check_deprecated(self):
        """Notifies user of deprecated config items"""
        captcha_config = self.config.get("captcha")
        if captcha_config is not None:
            if captcha_config.get("imagetypers") is not None:
                logger.warning(
                    'Captcha configuration for "imagetypers" (captcha/imagetypers) has been '
                    'renamed to "imagetyperz". '
                    'We found an outdated entry, which has to be renamed accordingly, in order '
                    'to be detected again.'
                )
            if captcha_config.get("driver_path") is not None:
                logger.warning(
                    'Captcha configuration for "driver_path" (captcha/driver_path) is no longer '
                    'required, as driver setup has been automated.'
                )

    def get(self, key, value=None):
        """Emulate dictionary"""
        return self.config.get(key, value)

    def _read_yaml_path(self, path, default_value=None):
        config = self.config
        parts = path.split('.')
        while len(parts) > 1:
            config = config.get(parts[0], {})
            parts = parts[1:]
        return config.get(parts[0], default_value)

    def database_location(self):
        """Return the location of the database folder"""
        config_database_location = self._read_yaml_path('database_location')
        if config_database_location is not None:
            return config_database_location
        if self.useEnvironment and Env.FLATHUNTER_DATABASE_LOCATION is not None:
            return Env.FLATHUNTER_DATABASE_LOCATION
        return os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/..")

    def set_searchers(self, searchers):
        """Update the active search plugins"""
        self.__searchers__ = searchers

    def searchers(self):
        """Get the list of search plugins"""
        return self.__searchers__

    def get_filter(self):
        """Read the configured filter"""
        builder = Filter.builder()
        builder.read_config(self.config)
        return builder.build()

    def target_urls(self):
        if self.useEnvironment and Env.FLATHUNTER_TARGET_URLS is not None:
            return Env.FLATHUNTER_TARGET_URLS.split(';')
        return self._read_yaml_path('urls', [])

    def verbose_logging(self):
        if self.useEnvironment and Env.FLATHUNTER_VERBOSE_LOG is not None:
            return True
        return self._read_yaml_path('verbose') is not None

    def loop_is_active(self):
        if self.useEnvironment and Env.FLATHUNTER_LOOP_PERIOD_SECONDS is not None:
            return True
        return self._read_yaml_path('loop.active', False)

    def loop_period_seconds(self):
        if self.useEnvironment and Env.FLATHUNTER_LOOP_PERIOD_SECONDS is not None:
            return int(Env.FLATHUNTER_LOOP_PERIOD_SECONDS)
        return self._read_yaml_path('loop.sleeping_time', 60 * 10)

    def has_website_config(self):
        if self.useEnvironment and Env.FLATHUNTER_WEBSITE_SESSION_KEY is not None:
            return True
        return 'website' in self.config

    def website_session_key(self):
        if self.useEnvironment and Env.FLATHUNTER_WEBSITE_SESSION_KEY is not None:
            return Env.FLATHUNTER_WEBSITE_SESSION_KEY
        return self._read_yaml_path('website.session_key', None)

    def website_domain(self):
        if self.useEnvironment and Env.FLATHUNTER_WEBSITE_DOMAIN is not None:
            return Env.FLATHUNTER_WEBSITE_DOMAIN
        return self._read_yaml_path('website.domain', None)

    def website_bot_name(self):
        if self.useEnvironment and Env.FLATHUNTER_WEBSITE_BOT_NAME is not None:
            return Env.FLATHUNTER_WEBSITE_BOT_NAME
        return self._read_yaml_path('website.bot_name', None)

    def captcha_enabled(self):
        """Check if captcha is configured"""
        return self._get_captcha_solver() is not None

    def get_captcha_checkbox(self):
        return self._read_yaml_path('captcha.checkbox', False)

    def get_captcha_afterlogin_string(self):
        return self._read_yaml_path('captcha.afterlogin_string', '')

    def google_cloud_project_id(self):
        if self.useEnvironment and Env.FLATHUNTER_GOOGLE_CLOUD_PROJECT_ID is not None:
            return Env.FLATHUNTER_GOOGLE_CLOUD_PROJECT_ID
        return self._read_yaml_path('google_cloud_project_id', None)

    def message_format(self):
        if self.useEnvironment and Env.FLATHUNTER_MESSAGE_FORMAT is not None:
            return '\n'.join(Env.FLATHUNTER_MESSAGE_FORMAT.split('#CR#'))
        config_format = self._read_yaml_path('message', None)
        if config_format is not None:
            return config_format
        return self.DEFAULT_MESSAGE_FORMAT

    def notifiers(self):
        if self.useEnvironment and Env.FLATHUNTER_NOTIFIERS is not None:
            return Env.FLATHUNTER_NOTIFIERS.split(",")
        return self._read_yaml_path('notifiers', None)

    def telegram_bot_token(self):
        if self.useEnvironment and Env.FLATHUNTER_TELEGRAM_BOT_TOKEN is not None:
            return Env.FLATHUNTER_TELEGRAM_BOT_TOKEN
        return self._read_yaml_path('telegram.bot_token', None)

    def telegram_notify_with_images(self) -> bool:
        flag = str(self._read_yaml_path("telegram.notify_with_images", 'false'))

        if self.useEnvironment and Env.FLATHUNTER_TELEGRAM_BOT_NOTIFY_WITH_IMAGES is not None:
            flag = str(Env.FLATHUNTER_TELEGRAM_BOT_NOTIFY_WITH_IMAGES)

        return flag.lower() == 'true'

    def telegram_receiver_ids(self):
        if self.useEnvironment and Env.FLATHUNTER_TELEGRAM_RECEIVER_IDS is not None:
            return [ int(x) for x in Env.FLATHUNTER_TELEGRAM_RECEIVER_IDS.split(",") ]
        return self._read_yaml_path('telegram.receiver_ids') or []

    def mattermost_webhook_url(self):
        if self.useEnvironment and Env.FLATHUNTER_MATTERMOST_WEBHOOK_URL is not None:
            return Env.FLATHUNTER_MATTERMOST_WEBHOOK_URL
        return self._read_yaml_path('mattermost.webhook_url', None)

    def _get_captcha_solver(self) -> Optional[CaptchaSolver]:
        """Get configured captcha solver"""
        if self.useEnvironment and Env.FLATHUNTER_IMAGETYPERZ_TOKEN is not None:
            imagetyperz_token = Env.FLATHUNTER_IMAGETYPERZ_TOKEN
        else:
            imagetyperz_token = self._read_yaml_path("captcha.imagetyperz.token", "")
        if imagetyperz_token:
            return ImageTyperzSolver(imagetyperz_token)

        if self.useEnvironment and Env.FLATHUNTER_2CAPTCHA_KEY is not None:
            twocaptcha_api_key = Env.FLATHUNTER_2CAPTCHA_KEY
        else:
            twocaptcha_api_key = self._read_yaml_path("captcha.2captcha.api_key", "")
        if twocaptcha_api_key:
            return TwoCaptchaSolver(twocaptcha_api_key)

        return None

    def get_captcha_solver(self) -> CaptchaSolver:
        solver = self._get_captcha_solver()
        if solver is not None:
            return solver
        raise Exception("No captcha solver configured properly.")

    def captcha_driver_arguments(self):
        if self.useEnvironment and Env.FLATHUNTER_HEADLESS_BROWSER is not None:
            return [
                "--no-sandbox",
                "--headless",
                "--disable-gpu",
                "--remote-debugging-port=9222",
                "--disable-dev-shm-usage",
                "window-size=1024,768"
            ]
        return self._read_yaml_path('captcha.driver_arguments', [])

    def use_proxy(self):
        """Check if proxy is configured"""
        return "use_proxy_list" in self.config and self.config["use_proxy_list"]
