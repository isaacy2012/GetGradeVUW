import os
import pickle
from os.path import isfile

from requests.cookies import cookiejar_from_dict

COOKIE_FILE = "cookies.cookie"


def save_cookies(browser):
    cookies = browser.session.cookies.get_dict()
    with open(COOKIE_FILE, "wb") as file:
        pickle.dump(cookies, file)


def load_cookies(browser):
    if not isfile(COOKIE_FILE):
        return

    with open(COOKIE_FILE, "rb") as file:
        browser.session.cookies = cookiejar_from_dict(pickle.load(file))

def delete_cookies():
    if not isfile(COOKIE_FILE):
        return
    os.remove(COOKIE_FILE)
