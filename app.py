import copy

from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from random import randint
import json
import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

recipes = dict()
recipes['breakfast'] = json.load(open('breakfast_cleaned.json', 'r', encoding='utf-8'))
recipes['lunch'] = json.load(open('lunch_cleaned.json', 'r', encoding='utf-8'))
recipes['dinner'] = json.load(open('dinner_cleaned.json', 'r', encoding='utf-8'))


@app.route('/', methods=['GET', 'OPTIONS'])
def index():

	# if request.method == 'OPTIONS':
	# 	return _build_cors_preflight_response()
	# elif request.method == 'GET':

	recipe_indexes = check_cookies_exist(request)

	recipes_to_convert = copy.deepcopy(recipe_indexes)
	convert_index_to_item(recipes_to_convert)

	res = make_response(jsonify(recipes_to_convert), 200)
	res.set_cookie('meals', json.dumps(recipe_indexes), httponly=True, samesite='None', secure=True)

	return res


@app.route('/get_recipe/<string:meal_type>')
def get_recipe(meal_type):
	try:
		return jsonify(recipes[meal_type][randint(0, len(recipes[meal_type]))])
	except:
		return abort(404, 'Invalid input given for endpoint: meal_type')


def check_cookies_exist(sent_request):
	if sent_request.cookies.get('meals'):
		return json.loads(request.cookies.get('meals'))
	return make_meal_plan()


def get_day(day):
	new_day = dict()

	recipe_list = [randint(0, len(recipes[i]) - 1) for i in recipes]
	new_day[day] = recipe_list
	return new_day


def make_meal_plan():
	new_week = get_weekdays()
	meal_plan = list(map(get_day, new_week))
	return meal_plan


def convert_index_to_item(indexes):

	for item in indexes:
		key = list(item.keys())[0]
		recipe_index_list = item.get(key)
		recipe_index_list = iter(recipe_index_list)
		recipe_list = [recipes[i][next(recipe_index_list)] for i in recipes]

		item.update({key: recipe_list})


def get_weekdays():
	td_day = datetime.timedelta(days=1)
	today = datetime.date.today()

	day_of_week = today.weekday()

	start = 0 - day_of_week
	end = 6 - day_of_week

	current_week = set()
	while start <= 0 or end >= 1:
		current_week.add(today + (td_day*start))
		current_week.add(today + (td_day*end))
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
	app.run(debug=True)
