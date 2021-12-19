import copy

from flask import Flask, jsonify, abort, make_response, request, g
from flask_cors import CORS
from random import randint
import json
from datetime import timedelta, date, datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

HEADER_NAME = 'Working-Week'

RECIPES = dict()

RECIPES['breakfast'] = json.load(open('breakfast_cleaned.json', 'r', encoding='utf-8'))
RECIPES['lunch'] = json.load(open('lunch_cleaned.json', 'r', encoding='utf-8'))
RECIPES['dinner'] = json.load(open('dinner_cleaned.json', 'r', encoding='utf-8'))


@app.before_request
def before_request_func():
	if request.method == 'GET':
		if request.headers.get(HEADER_NAME):
			g.selected_week = request.headers.get(HEADER_NAME)
		else:
			g.selected_week = 'blank-header'

		if check_cookies_exist(request, g.get('selected_week')):
			if check_if_shift_needed(request.cookies.get('current-week')):
				g.cookie_data = {
					'previous-week': json.loads(request.cookies.get('current-week')),
					'current-week': json.loads(request.cookies.get('upcoming-week')),
					'upcoming-week': make_new_meal_plan(advance_week=True)
				}
			else:
				g.cookie_data = {g.get('selected_week'): json.loads(request.cookies.get(g.get('selected_week')))}
	elif request.method == 'POST':
		g.selected_week = request.headers.get(HEADER_NAME)
		g.cookie_data = json.loads(request.cookies.get(g.get('selected_week')))


def check_cookies_exist(sent_request, week_header):
	try:
		if sent_request.cookies.get(week_header):
			g.cookies_exist = True
			return True
		else:
			g.cookies_exist = False
			return False
	except KeyError:
		return abort(500, 'Issue attempting to verify cookies: ' + str(KeyError))


def check_if_shift_needed(cookie):
	if not cookie:
		return False
	current_week = json.loads(cookie)

	td_week = timedelta(weeks=1)
	today = datetime.fromisoformat(date.isoformat(date.today()))
	first_day_of_plan = datetime.strptime(list(current_week[0].keys())[0], '%A %b %d, %Y')
	need_to_shift_weeks = first_day_of_plan + td_week <= today

	return need_to_shift_weeks


@app.route('/', methods=['GET', 'OPTIONS'])
def return_fetch_data():

	# if request.method == 'OPTIONS':
	# 	return _build_cors_preflight_response()
	# elif request.method == 'GET':

	if g.get('cookies_exist'):
		recipe_indexes = g.get('cookie_data')[g.get('selected_week')]
	else:
		if g.get('selected_week') == 'upcoming-week':
			recipe_indexes = make_new_meal_plan(advance_week=True)
		else:
			recipe_indexes = make_new_meal_plan()

	converted_recipes = convert_index_to_recipe_data(recipe_indexes)
	http_response = create_http_response(converted_recipes, recipe_indexes)

	return http_response


@app.route('/replace_current_meal_plan')
def replace_current_meal_plan():
	if g.get('selected_week') == 'upcoming-week':
		new_recipe_indexes = make_new_meal_plan(advance_week=True)
	else:
		new_recipe_indexes = make_new_meal_plan()

	g.get('cookie_data').update({g.get('selected_week'): new_recipe_indexes})
	converted_recipes = convert_index_to_recipe_data(new_recipe_indexes)

	http_response = create_http_response(converted_recipes, new_recipe_indexes)
	return http_response


@app.route('/replace_selected_recipes/<int:selected_day>', methods=['POST'])
def replace_selected_recipes(selected_day):
	form_data = json.loads(request.data)
	recipe_indexes = g.get('cookie_data')
	selected_day_key = list(recipe_indexes[selected_day].keys())[0]
	used_recipes = {
		f'{count}x{index}' for item in recipe_indexes
		for value in item.values() for count, index in enumerate(value)
	}

	for count, item in enumerate(form_data.get('selected-items')):
		if item:
			meal_type = list(RECIPES.keys())[count]
			new_recipe_index = randint(0, len(RECIPES[meal_type]))
			while f'{count}x{new_recipe_index}' in used_recipes:
				new_recipe_index = randint(0, len(RECIPES[list(RECIPES.keys())[count]]))
			else:
				recipe_indexes[selected_day][selected_day_key][count] = new_recipe_index

	recipe_data = convert_index_to_recipe_data(recipe_indexes)
	res = create_http_response(recipe_data, recipe_indexes)
	return res


@app.route('/get_recipe/<string:meal_type>')
def get_recipe(meal_type):
	try:
		return jsonify(RECIPES[meal_type][randint(0, len(RECIPES[meal_type]))])
	except KeyError:
		return abort(404, 'Invalid input given for endpoint: meal_type')


def create_http_response(recipe_data, recipe_indexes):
	res = make_response(jsonify(recipe_data), 200)

	try:
		expire_date = get_expiration_date(recipe_indexes)

		if request.headers.get(HEADER_NAME):
			if g.get('cookies_exist'):
				for key, value in g.get('cookie_data').items():
					expire_date = get_expiration_date(value)
					res.set_cookie(
						key, json.dumps(value),
						httponly=False, samesite='None', secure=True, expires=expire_date
					)
			else:
				res.set_cookie(
					g.get('selected_week'), json.dumps(recipe_indexes),
					httponly=False, samesite='None', secure=True, expires=expire_date
				)
		else:
			res.set_cookie(
				'blank-header', json.dumps(recipe_indexes),
				httponly=False, samesite='None', secure=True, expires=expire_date
			)
	except ValueError:
		return abort(500, 'Error attempting to create new cookie: ' + str(ValueError))

	return res


def get_expiration_date(recipe_indexes):
	td_day = timedelta(days=1)
	first_day_of_plan = datetime.strptime(list(recipe_indexes[0].keys())[0], '%A %b %d, %Y')
	return first_day_of_plan + (td_day * (14 - first_day_of_plan.weekday()))


def get_day(day):
	new_day = dict()

	recipe_list = [randint(0, len(RECIPES[i]) - 1) for i in RECIPES]

	new_day[day] = recipe_list
	return new_day


def make_new_meal_plan(advance_week=False):
	new_week = get_weekdays(advance_week)
	meal_plan = list(map(get_day, new_week))
	check_for_duplicate_recipes(meal_plan)
	return meal_plan


def check_for_duplicate_recipes(meals):

	used_recipes = set()

	for item in meals:
		for index_list in item.values():
			for x, y in enumerate(index_list):
				recipe_index = f'{x}x{y}'
				if recipe_index in used_recipes:
					new_index = randint(0, len(RECIPES[list(RECIPES.keys())[x]]) - 1)
					while f'{x}x{new_index}' in used_recipes:
						new_index = randint(0, len(RECIPES[list(RECIPES.keys())[x]]) - 1)
					index_list[x] = new_index
				else:
					used_recipes.add(recipe_index)


def convert_index_to_recipe_data(indexes):

	recipes_to_convert = copy.deepcopy(indexes)

	for item in recipes_to_convert:
		key = list(item.keys())[0]
		recipe_index_list = item.get(key)
		recipe_index_list = iter(recipe_index_list)
		recipe_list = [RECIPES[i][next(recipe_index_list)] for i in RECIPES]

		item.update({key: recipe_list})
	return recipes_to_convert


def get_weekdays(advance_week):
	td_day = timedelta(days=1)

	if advance_week:
		base_date = date.today() + (td_day * 7)
	else:
		base_date = date.today()

	day_of_week = base_date.weekday()

	start = 0 - day_of_week
	end = 6 - day_of_week

	current_week = set()
	while start <= 0 or end >= 1:
		current_week.add(base_date + (td_day*start))
		current_week.add(base_date + (td_day*end))
		start += 1
		end -= 1
	else:
		current_week = list(current_week.copy())
		current_week.sort()
	return [i.strftime('%A %b %d, %Y') for i in current_week]


# Need to set up specific CORS headers
# def _build_cors_preflight_response():
# 	response = make_response()
# 	response.headers.add('Access-Control-Allow-Origin', '*')
# 	response.headers.add('Access-Control-Allow-Headers', '*')
# 	response.headers.add('Access-Control-Allow-Methods', '*')
# 	return response
#
#
# def _corify_actual_response(response):
# 	response.headers.add('Access-Control-Allow-Origin', '*')
# 	return response


if __name__ == '__main__':
	app.run(debug=True, host='localhost')
