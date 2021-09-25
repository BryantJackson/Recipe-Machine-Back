from bs4 import BeautifulSoup
from math import ceil
from sys import argv, stdout
from time import sleep
import requests
import re
import json
import concurrent.futures


stdout.reconfigure(encoding='utf-8')
MAX_THREADS = 30
try:
    RECIPE_URLS = json.load(open(argv[1], 'r', encoding='utf-8'))
except FileNotFoundError:
    print('File not found. Valid filepath required for json information')


def get_html_data(url):
    res = requests.get(url)

    if res.status_code != 200:
        raise RuntimeError(f'Error fetching data: {res.status_code}, on URL: {url}')
    sleep(0.25)
    soup = BeautifulSoup(res.content, 'html.parser')

    html_info = json.loads(soup.find('script', type="application/ld+json").string)

    return build_recipe(html_info)


def build_recipe(html_data):
    new_recipe = dict()
    new_recipe['url'] = html_data[1]['mainEntityOfPage']
    new_recipe['name'] = html_data[1]['name']
    new_recipe['prep'] = parse_time(html_data[1]['prepTime'])
    new_recipe['cook'] = parse_time(html_data[1]['cookTime'])
    new_recipe['ready in'] = parse_time(html_data[1]['totalTime'])
    new_recipe['servings'] = html_data[1]['recipeYield']
    new_recipe['ingredients'] = html_data[1]['recipeIngredient']
    for x in html_data[1].items():
        if x[0] == 'recipeInstructions':
            new_recipe['directions'] = []
            for i in x[1]:
                new_recipe['directions'].append(i['text'])
        if x[0] == 'nutrition':
            cal = x[1]['calories'].split(' ')[0]
            new_recipe['calories'] = ceil(float(cal))
            new_recipe['carb'] = parse_nutrition(x[1]['carbohydrateContent'])
            new_recipe['protein'] = parse_nutrition(x[1]['proteinContent'])
            new_recipe['fat'] = parse_nutrition(x[1]['fatContent'])
    return new_recipe


def parse_nutrition(nutr):
    if not nutr:
        return 'n/a'
    return ceil(float(nutr[:-1]))


def parse_time(t_duration):
    if not t_duration:
        return 'n/a'
    result = re.search('([0-9]+H)([0-9]+M)', t_duration)
    new_time = result.group()
    if new_time[0] == '0':
        new_time = new_time[2:].replace('M', ' Mins')
    else:
        new_time = new_time.replace('H', ' Hours ').replace('M', ' Mins')
    return new_time


def scrape_recipe_urls(recipe_urls):
    threads = min(MAX_THREADS, len(recipe_urls))

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        return list(executor.map(get_html_data, [res['url'] for res in recipe_urls]))


def main():
    cleaned_recipes = scrape_recipe_urls(RECIPE_URLS)
    print(json.dumps(cleaned_recipes, indent=2))


main()
