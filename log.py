from datetime import datetime, timedelta

LOG_FILE = "log.txt"


def log(string: str):
    """
    Log a string
    :param string:
    """
    f = open(LOG_FILE, "a")
    f.write(string)
    f.write("\n")
    f.close()


def log_sleep(minutes: float):
    """
    Log the sleep
    :param minutes:
    :return:
    """
    now = datetime.now()
    delta = timedelta(minutes=minutes)
    time_str = (now + delta).strftime("%Y-%m-%d %H:%M:%S")

    print_log("Sleeping for: " + "{:.2f}".format(minutes) + " minutes, until " + time_str)


def print_log(string: str):
    """
    Log and print a string
    :param string:
    """
    print(string)
    log(string)


def clear():
    """
    Clear the log
    """
    f = open(LOG_FILE, "w")
    f.close()
