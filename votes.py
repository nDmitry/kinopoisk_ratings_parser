from datetime import datetime
import csv
from http.cookies import SimpleCookie
import re
import requests
from bs4 import BeautifulSoup

import translators as ts
from cookies_file import sting_cookies, numer_user


def format_cookies(raw_cookies):
    """Convert raw cookie string into a dictionary."""
    cookie = SimpleCookie()
    cookie.load(raw_cookies)
    cookies = {}
    for key, morsel in cookie.items():
        cookies[key] = morsel.value
    return cookies


def format_date(date):
    """Convert date string into a specific format."""
    date_object = datetime.strptime(date, "%d.%m.%Y, %H:%M")
    formatted_date = date_object.strftime("%Y-%m-%d")
    return formatted_date


def get_year(year_and_type):
    """Extract year from a combined string of year and type."""
    try:
        year = year_and_type.split(",")[1]
    except IndexError:
        year = year_and_type.split(",")[0]
    return year


def get_type_(year_and_type):
    """Extract type from a combined string of year and type."""
    type_ = year_and_type.split(",")[0]
    try:
        type_ = int(type_)
        type_ = "film"
    except ValueError:
        pass
    return type_


def detect_shortfilm(type_, duration):
    """Detect if a film is a short film based on its duration."""
    if type_ == "film" and int(duration) <= 55:
        type_ = "short-film"
    return type_


def get_page_content(page_num, cookies):
    """Fetch page content from a URL."""
    response = requests.get(
        f"https://www.kinopoisk.ru/user/{numer_user}/votes/list/vs/vote/page/{page_num}/#list",
        cookies=cookies,
        timeout=30,
    )

    soup = BeautifulSoup(response.text, "lxml")  # html.parser
    items = soup.select(".profileFilmsList .item")
    return items


def translate_type(type_):
    """Translate type from Russian to English."""
    if type_ == "сериал":
        type_eng = "series"
    elif type_ == "мини-сериал":
        type_eng = "mini-series"
    else:
        type_eng = type_
    return type_eng


def get_rating_from_script(item):
    """Extract rating from JavaScript code in the item."""
    # Find all script tags in the item
    scripts = item.find_all("script")

    for script in scripts:
        if script.string and "ur_data.push" in script.string:
            # Use regex to find rating value
            match = re.search(r"rating:\s*'(\d+)'", script.string)
            if match:
                return match.group(1)

    return None


def write_to_csv(items, writer):
    """Write items to a CSV file."""
    for item in items:
        print(item)
        num = item.find("div", class_="num").text
        name_eng = item.find("div", class_="nameEng").text
        name_rus = item.find("div", class_="nameRus").text.split("(")[0].strip()
        if name_eng == " ":
            name_eng = ts.translate_text(name_rus)
        year_and_type = item.find("div", class_="nameRus").text.split("(")[1][:-1]
        year = get_year(year_and_type).strip()
        duration = item.find("div", class_="rating").text.strip().split("\n")[-1][:-5]
        type_ = get_type_(year_and_type)
        type_ = detect_shortfilm(type_, duration)
        type_eng = translate_type(type_)
        date = format_date(item.find("div", class_="date").text)

        # Extract rating from JavaScript code
        vote_10 = get_rating_from_script(item)
        if vote_10 is None:
            print(f"Warning: Could not find rating for item {num}")
            continue

        vote_lb = float(vote_10) / 2

        writer.writerow(
            {
                "Num": num,
                "Date": date,
                "Name": name_eng,
                "NameRus": name_rus,
                "Rating_10": vote_10,
                "Rating": vote_lb,
                "Year": year,
                "Duration": duration,
                "Type": type_eng,
            }
        )


def main():
    """Main function to run the script."""
    raw_cookies = sting_cookies
    cookies = format_cookies(
        raw_cookies
    )  # withour cookies don't work multiple responses
    page_num = 1
    with open("votes.csv", "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "Num",
            "Date",
            "Name",
            "NameRus",
            "Rating_10",
            "Rating",
            "Year",
            "Duration",
            "Type",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        while True:
            items = get_page_content(page_num, cookies)
            if not items:
                break
            write_to_csv(items, writer)
            page_num += 1


if __name__ == "__main__":
    main()
