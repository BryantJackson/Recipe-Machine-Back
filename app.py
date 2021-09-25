from flask import Flask, jsonify, abort
from flask_cors import CORS
from random import randint
import json
import datetime

app = Flask(__name__)
CORS(app)

recipes = dict()
recipes['breakfast'] = json.load(open('breakfast_cleaned.json', 'r', encoding='utf-8'))
recipes['lunch'] = json.load(open('lunch_cleaned.json', 'r', encoding='utf-8'))
recipes['dinner'] = json.load(open('dinner_cleaned.json', 'r', encoding='utf-8'))


@app.route('/', methods=['GET', 'OPTIONS'])
def index():
	# recipe_data = list()
	# recipe_data.append(recipes['breakfast'][randint(0, 50)])
	# recipe_data.append(recipes['lunch'][randint(0, 50)])
	# recipe_data.append(recipes['dinner'][randint(0, 50)])

	# if request.method == 'OPTIONS':
	# 	return _build_cors_preflight_response()
	# elif request.method == 'GET':
	return jsonify(make_mealplan())


@app.route('/get_recipe/<string:meal_type>')
def get_recipe(meal_type):
	try:
		return jsonify(recipes[meal_type][randint(0, len(recipes[meal_type]))])
	except:
		return abort(404, 'Invalid input given for endpoint: meal_type')


def get_day(day):
	new_day = dict()
	recipe_list = [recipes[i][randint(0, len(recipes[i]) -1 )] for i in recipes]
	new_day[day] = recipe_list
	return new_day


def make_mealplan():
	new_week = get_weekdays()
	meal_plan = list(map(get_day, new_week))
	return meal_plan


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
