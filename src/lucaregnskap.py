import asyncio
import aiohttp
import json
from bs4 import BeautifulSoup
from dataclasses import dataclass

"""
This program scrapes all the accounts from https://www.lucaregnskap.no/kontobeskrivelser/1000 to 8990
and writes them to a json file, ready to be used for whichever purpose. The scraping is done using aiohttp and asyncio, 
the parsing is done using BeautifulSoup.

The data is used for accounting software, to make it easier to find the correct account for a given transaction.
Useful if you want to visually represent the transactions in a ledger, or if you want to make a program that
automatically finds the correct account for a given transaction.

I have no affiliation with lucaregnskap.no, I just found they had a nice list of accounts descriptions,
I hope they don't mind.


USAGE (assuming the script is located in the same folder as your main file):
----------------------------------------------------------------------------

import lucaregnskap

if __name__ == '__main__':
    accounts = lucaregnskap.get_accounts()
    print(accounts['1000'])
    for id, account in accounts.items():
        print(id, account['tittel'], account['beskrivelse'])


# Alternatively just read the json file that is created when you run this directly:
accounts = json.loads(open('lucaregnskap.json', 'r', encoding='utf-8').read())
print(accounts['1000'])
"""


ACCOUNTS_FILE = 'lucaregnskap.json'
START = 1000
END = 8990
QUERIES = ['https://www.lucaregnskap.no/kontobeskrivelser/' + str(i)
           for i in range(START, END + 1)]


@dataclass
class Konto:
    """Represents a single account"""
    id: str
    tittel: str
    beskrivelse: str


def parse_konto(html: str) -> Konto:
    """Parses the html and returns a Konto object with the id, title and description"""
    soup = BeautifulSoup(html, 'html.parser')
    headers = soup.find_all('h1')

    acc_id = headers[0].text.replace('Konto: ', '')
    title = headers[1].text
    description = soup.find('div', {'class': 'account-description'})

    links = description.find_all('a')
    for link in links:
        link.replace_with(f"{link.text} ({link.attrs.get('title')})")

    return Konto(acc_id, title, description.text.strip())


async def scrape(url) -> str | None:
    """Scrapes the given url and returns the html as a string, or None if the page does not exist"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            elif response.status == 404:
                return None
            else:
                raise Exception(f'[ERROR] Got status code: {response.status}')


async def scrape_queries(queries: list) -> None:
    """Scrapes all the given queries and writes the results to a json file"""
    tasks = [asyncio.create_task(scrape(query)) for query in queries]
    htmls = await asyncio.gather(*tasks)

    # Remove None values
    htmls = [html for html in htmls if html is not None]

    # Find all accounts, and convert them to Konto objects
    kontoer = [parse_konto(str(html)) for html in htmls]

    # Write to json
    json_data = {konto.id: {'tittel': konto.tittel, 'beskrivelse': konto.beskrivelse} for konto in kontoer}
    with open(ACCOUNTS_FILE, 'w+', encoding='utf-8') as f:
        f.write(json.dumps(json_data, ensure_ascii=False, indent=4))

    # Stop the loop
    asyncio.get_event_loop().stop()


def scrape_async() -> None:
    """Scrapes all the queries asynchronously, by creating a new event loop and running it until completion"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scrape_queries(QUERIES))


def get_accounts() -> dict:
    """Returns a dictionary of all accounts, using the account id as the key"""
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            print(f'[INFO] Reading from {ACCOUNTS_FILE}')
            return json.loads(f.read())
    except FileNotFoundError:
        print(f'[INFO] {ACCOUNTS_FILE} not found, scraping...')
        scrape_async()
        return get_accounts()


if __name__ == '__main__':
    print('You should not run this file directly, but instead import it and call get_accounts()')
    print('Unless you want to force-scrape the websites again, do you? (y/n)')
    if input().lower() == 'y':
        scrape_async()
        print('Done! You can now import lucaregnskap and call get_accounts()')
    else:
        print('Ok, bye!')
