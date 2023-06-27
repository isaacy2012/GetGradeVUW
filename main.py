import os
import time
import webbrowser
from datetime import datetime
from random import random
from random import seed
from typing import List, Any

import mechanicalsoup
from bs4 import BeautifulSoup
from mechanicalsoup import LinkNotFoundError
from tinydb import TinyDB, Query

import config
import cookies
import gmail
import log


class VUWResult:
    def __init__(self, course_code: str, course_title: str, mark: str):
        self.course_code = course_code
        self.course_title = course_title
        self.mark = mark

    def email_format_space(self, minlen: int) -> str:
        """
        Format with spaces, padding between : and mark to reach minlen
        :param minlen: the minimum length
        :return:
        """
        diff = minlen - len(self.email_format())
        spaces = " " * diff
        return str(self.course_title) + ": " + spaces + str(self.mark)

    def complete(self) -> bool:
        return self.mark != " "

    def email_format(self) -> str:
        """
        Format for email
        :return:
        """
        return str(self.course_title) + ": " + str(self.mark)

    def __str__(self):
        if self.mark == " ":
            return str(self.course_code) + ": " + str(self.course_title) + ": " + "[none]" + "\n"
        else:
            return str(self.course_code) + ": " + str(self.course_title) + ": " + str(self.mark) + "\n"

    def __repr__(self):
        return str(self)


def format_results(results: List[VUWResult]) -> str:
    """
    Format a list of VUWResults
    :param results:
    :return:
    """
    str_list = []

    # Find the max size to align mark with
    maxlen = 0
    for result in results:
        currlen = len(result.email_format())
        if currlen > maxlen:
            maxlen = currlen

    # Append to string list
    for result in results:
        str_list.append(result.email_format_space(maxlen) + "\n")

    return "".join(str_list)


def email_aliveness_check():
    gmail.send_email("Hello from GetGradeVUW!",
                     "This message is to let you know that GetGradeVUW started successfully.")


def _email_results(subject: str, new_results: List[VUWResult]):
    """
    Emails the new results
    :param subject: the subject of the email
    :param new_results: the new results
    """
    gmail.send_email(subject, format_results(new_results))


def email_initial_results(results: List[VUWResult]):
    _email_results("GetGradeVUW Initialised With Grades", results)


def email_subsequent_results(new_results: List[VUWResult]):
    _email_results("New VUW Results" if len(new_results) > 1 else "New VUW Result", new_results)


ACADEMIC_HISTORY_LINK = "/pls/webprod/bwsxacdh.P_FacStuInfo"


def login(browser: mechanicalsoup.StatefulBrowser):
    """
    Login to VUW student records with the browser
    :param browser: the StatefulBrowser to login with
    :return:
    """
    browser.select_form("form[action^=\"/adfs/ls\"]")
    browser["UserName"] = config.get_username()
    browser["Password"] = config.get_password()
    browser.submit_selected()
    #
    # browser.select_form("form[method=\"post\"]")
    # browser.submit_selected()
    log.print_log("Logging In:")
    time.sleep(1)

    log.print_log("1/3...")
    # print("1================================================================")
    # print(browser.page.prettify)

    browser.select_form("form[method=\"POST\"]")
    browser.submit_selected()

    log.print_log("2/3...")
    time.sleep(1)

    # print("2================================================================")
    # print(browser.page.prettify)

    browser.select_form("form[method=\"post\"]")
    browser.submit_selected()

    log.print_log("3/3...")
    time.sleep(1)

    # browser.open("https://student-records.vuw.ac.nz/pls/webprod/bwsxacdh.P_FacStuInfo")
    # print("3================================================================")
    # print(browser.page.prettify)
    # print(browser.page.find_all('a'))
    browser.follow_link(ACADEMIC_HISTORY_LINK)


def get_entry_indices(entry: List[Any]):
    """
    Gets the indices of the course, title, and grade, given the entry
    :param entry:
    :return:
    """
    course_index = -1
    title_index = -1
    grade_index = -1
    count = 0
    for column in entry:
        if column.text == "Course":
            course_index = count
        elif column.text == "Title":
            title_index = count
        elif column.text == "Grade":
            grade_index = count

        count += 1

    if grade_index == -1 or course_index == -1 or title_index == -1:
        raise ValueError("An index was -1: " +
                         " grade_index = " + str(grade_index) +
                         " course_index = " + str(course_index) +
                         " title_index = " + str(title_index)
                         )

    return course_index, title_index, grade_index


def query(db: TinyDB, epoch: int):
    """
    Query and send email
    :param db: the database
    :param epoch: the number of successful tries since the program was started
    """
    browser = mechanicalsoup.StatefulBrowser()
    cookies.load_cookies(browser)
    browser.open("https://studentrecords.vuw.ac.nz/")
    browser.select_form("form[method=\"post\"]")
    browser.submit_selected()

    browser.select_form("form[method=\"post\"]")
    browser.submit_selected()

    try:
        browser.follow_link(ACADEMIC_HISTORY_LINK)
    except LinkNotFoundError:
        cookies.delete_cookies()
        login(browser)
    else:
        log.print_log("Successfully logged in with cookies!")

    # print("4================================================================")
    # print(browser.page.prettify)
    cookies.save_cookies(browser)

    # At this point, we have the page with the grades
    page = str(browser.page)
    soup = BeautifulSoup(page, "html.parser")
    tables = soup.find_all("table", {"summary": "This table displays the student course history information."})

    # Full list of results
    results = []

    for table in tables:
        entries = table.find_all("tr")
        course_index, title_index, grade_index = get_entry_indices(entries[0].find_all("th"))
        for i in range(1, len(entries) - 1):
            columns = entries[i].find_all("td")
            course = columns[course_index].text
            title = columns[title_index].text
            grade = columns[grade_index].text
            results.append(VUWResult(course, title, grade))

    # New results
    new_results = []

    # Check for each result, whether the database already contains it
    for result in results:
        if not result.complete():
            continue

        entry_query = Query()
        db_result = db.search(
            (entry_query.course_code == result.course_code) & (entry_query.course_title == result.course_title) & (
                    entry_query.mark == result.mark))
        if (len(db_result)) == 0:
            db.insert({"course_code": result.course_code, "course_title": result.course_title, "mark": result.mark})
            new_results.append(result)

    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if epoch > 0:
        if len(new_results) > 0:
            log.print_log("Email sent at: " + time_str)
            log.log("=================NEW RESULTS=================")
            log.log(format_results(new_results))
            log.log("=============================================")
            email_subsequent_results(new_results)
        else:
            log.print_log("No new results at: " + time_str)
    else:
        log.print_log("Initialized " + str(len(results)) + " results at: " + time_str)
        log.print_log("===============INITIAL RESULTS===============")
        log.print_log(format_results(new_results))
        log.print_log("=============================================")
        email_initial_results(new_results)


def wait_on_exception():
    """
    Wait a few minutes when there is an exception
    :return:
    """
    sleep_seconds = 60 + (random() * (180 - 60))
    log.print_log("Waiting for " + str(int(sleep_seconds)) + " seconds to retry, until")
    time.sleep(sleep_seconds)


def main():
    db = TinyDB("db.json")
    # Drop tables
    db.drop_tables()

    # Clear the log
    log.clear()

    # Initialize gmail
    gmail.init()

    email_aliveness_check()

    seed()
    epoch = 0
    while True:
        if config.within_active_hours():
            try:
                query(db, epoch)
            except ConnectionError as e:
                log.print_log(f"ConnectionError Handled {e}")
                wait_on_exception()
            except Exception as e:
                log.print_log(f"Other Error Handled {e}")
                wait_on_exception()
            else:
                # Sleep
                sleep_minutes = 15 + (random() * (30 - 15))
                log.log_sleep(sleep_minutes)
                time.sleep(sleep_minutes * 60)
            finally:
                epoch += 1
        else:
            sleep_seconds = config.seconds_till_active_hours_begin()
            log.log_sleep(sleep_seconds / 60.0)
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
