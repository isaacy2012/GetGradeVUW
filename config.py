from datetime import datetime, timedelta
from os.path import isfile
from typing import Tuple

from cryptography.fernet import Fernet
import configparser

SECRET_FILE = "config_secret.key"

EMAIL = "email"
USERNAME = "username"
PASSWORD = "password"
ACTIVE_HOURS = "active_hours"

CONFIG_FILE = "settings.ini"
SETTINGS_HEADER = "SETTINGS"


def _generate_key():
    """
    Generates a key and saves it into a file
    """

    key = Fernet.generate_key()
    with open(SECRET_FILE, "wb") as key_file:
        key_file.write(key)


def _load_key():
    """
    Loads the key named secret.key from the current directory
    :return: the key
    """
    if not isfile(SECRET_FILE):
        _generate_key()

    return open(SECRET_FILE, "rb").read()


def _get_encrypted_data(name: str) -> str:
    """
    gets the encrypted data
    :param name: the settings name to get from
    :return: the decrypted data
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    encrypted = config[SETTINGS_HEADER][name].encode("ascii")
    return Fernet(_load_key()).decrypt(encrypted).decode()


def _get_data(name) -> str:
    """
    gets the unencrypted data
    :param name: the settings name to get from
    :return: the decrypted data
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config[SETTINGS_HEADER][name]


def get_password() -> str:
    """
    returns the users password, calling init() first
    :return: the password stored in the email file
    """
    _init()
    return _get_encrypted_data(PASSWORD)


def get_username() -> str:
    """
    returns the users username, calling init() first
    :return: the username stored in the email file
    """
    _init()
    return _get_encrypted_data(USERNAME)


def get_email_address() -> str:
    """
    returns the users email address, calling init() first
    :return: the email address stored in the email file
    """
    _init()
    return _get_encrypted_data(EMAIL)


def _get_active_hours() -> Tuple[int, int]:
    """
    :return: the active hours as a Tuple[start: int, end: int]
    """
    string = _get_data(ACTIVE_HOURS)
    splits = string.split("-")
    if len(splits) != 2:
        return 0, 24
    else:
        return int(splits[0]), int(splits[1])


def within_active_hours() -> bool:
    """
    :return: whether it is currently within active hours
    """
    _init()
    start, end = _get_active_hours()
    hour = datetime.now().hour
    if start < end:
        return start <= hour < end
    else:
        return hour >= start or hour < end


def seconds_till_active_hours_begin() -> int:
    """
    :return: the seconds until the active hours, or 0 if it is currently active hours
    """
    # _init() call in within_active_hours
    if within_active_hours():
        return 0

    now = datetime.now()
    start, _ = _get_active_hours()
    restart = datetime.now()
    restart = restart.replace(hour=start, minute=0, second=0, microsecond=0)
    if start < now.hour:
        one_day = timedelta(days=1)
        restart = restart + one_day

    return int((restart - now).total_seconds()) + 1


def _init():
    """
    Initialises the configuration. Queries the user if any of the files dont exist
    """
    if not isfile(SECRET_FILE):
        _generate_key()

    if not isfile(CONFIG_FILE):
        print("This is the first time running GetGrade. Please enter:")
        config = configparser.ConfigParser()
        fernet = Fernet(_load_key())
        config[SETTINGS_HEADER] = {
            EMAIL: fernet.encrypt(input("Email address to send to:").encode()).decode(),
            USERNAME: fernet.encrypt(input("Username:").encode()).decode(),
            PASSWORD: fernet.encrypt(input("Password:").encode()).decode(),
            ACTIVE_HOURS: "",
        }
        with open(CONFIG_FILE, "w") as configfile:
            config.write(configfile)
