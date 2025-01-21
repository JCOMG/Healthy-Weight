import math
import os
from datetime import datetime
from uuid import uuid4
from PIL import Image
from pyzbar.pyzbar import decode

import requests
from email_validator import validate_email, EmailNotValidError
from flask import render_template, redirect, url_for, flash, request, jsonify, logging, session, Response
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app import app, db
from app.forms import LoginForm, RegistrationForm, AddStudentForm, BorrowForm, \
    UploadStudentsForm, ToggleActiveForm, UploadUsersForm, DamageForm, SearchStudentForm, UploadPicturesForm, \
    UpdateForm, AccountStatusForm, ListUsersForm, ForgotForm, Fine
from app.models import Student, Loan, User, FoodLog
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from app.llama3 import GroqChatClient

import pandas as pd


@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')


@app.route('/show_Body_status', methods=['GET', 'POST'])
def show_body_status():
    show = False
    if request.method == 'POST':
        show = True
    return render_template('index.html', show=show)


@app.route('/Calculate_BMR', methods=['GET', 'POST'])
def BMR():
    new_weight = 0
    nutrients = True
    days = None
    if request.method == 'POST':
        formula = request.form['BmrRmr']
        print(formula)
        gender = request.form['gender']
        weight = float(request.form['weight'])
        session['weight'] = weight
        height = float(request.form['height'])
        session['height'] = height
        age = int(request.form['age'])
        session['age'] = age
        activity_level = request.form['activity_level']
        days = int(request.form['days'])
        fitness_goal = request.form['fitness_goal']
        session['fitness_goal'] = fitness_goal
        session['BmrRmr'] = formula
        session['gender'] = gender
        session['weight'] = weight
        session['height'] = height
        session['age'] = age
        session['activity_level'] = activity_level
        session['days'] = days
        nutrients = calculate_nutrients(formula, gender, weight, height, age, activity_level, fitness_goal)

        new_weight = round(
            dynamic_weight_change(formula, gender, weight, height, age, activity_level, nutrients['calories'],
                                  days, fitness_goal))

    return render_template('index.html', nutrients=nutrients, days=days, new_weight=new_weight,
                           fitness_goal=fitness_goal)


def calculate_bmr(gender, weight, height, age):
    if gender == "male":
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)


def calculate_tdee(bmr, activity_level):
    return bmr * float(activity_level)


def calculate_nutrients(formula, gender, weight, height, age, activity_level, fitness_goal):
    # Use this formula to calculate BMR or RMR
    bmr = 0
    rmr = 0
    tdee = 0
    if formula == "BMR formula : The Harris-Benedict Equation (revised by Roza and Shizgal in 1984)":
        if gender == "male":
            bmr = 88.362 + (weight * 13.397) + (height * 4.799) - (age * 5.677)
        else:
            bmr = 447.593 + (weight * 9.247) + (height * 3.098) - (age * 4.330)
        print(bmr)

    elif formula == "BMR formula :Mifflin-St. Jeor in 1990":
        if gender == "male":
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        print(bmr)

    elif formula == "RMR formula : Pavlidou (Proposed New Equations), in kcal/d (2022)":
        if gender == "male":
            rmr = (9.65 * weight + 5.73 * height) - 5.08 * age + 260
        else:
            rmr = (7.38 * weight + 6.07 * height) - 2.31 * age + 43
    if bmr > 0:
        tdee = bmr * float(activity_level)
    else:
        bmr = 0
    if rmr > 0:
        tdee = rmr * float(activity_level)
    else:
        rmr = 0
    print(f"tdee : {tdee}")

    if fitness_goal == "gain":
        recommend_tdee_calorie = tdee + 300  # increase 300 grams for energy deficit
        print(f"recommend : {recommend_tdee_calorie}")
        protein = weight * 1.2
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        carbs_percent = (recommend_tdee_calorie - protein * 4 - fat * 9) / recommend_tdee_calorie  # 4 calories per gram
        carbs = (recommend_tdee_calorie * carbs_percent) / 4
    elif fitness_goal == "lose":
        recommend_tdee_calorie = tdee - 300  # decrease 300 grams for energy deficit

        protein = weight * 1.2
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        carbs_percent = (recommend_tdee_calorie - protein * 4 - fat * 9) / recommend_tdee_calorie  # 4 calories per gram
        carbs = (recommend_tdee_calorie * carbs_percent) / 4  # 4 calories per gram
    else:  # "maintain"
        recommend_tdee_calorie = tdee
        # Nutrient breakdown
        protein = weight * 1.2
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        carbs_percent = (recommend_tdee_calorie - protein * 4 - fat * 9) / recommend_tdee_calorie  # 4 calories per gram
        carbs = (recommend_tdee_calorie * carbs_percent) / 4  # 4 calories per gram

    print(recommend_tdee_calorie)
    print(tdee)
    return {
        'calories': round(recommend_tdee_calorie),
        'carbs': round(carbs),
        'protein': round(protein),
        'fat': round(fat),
        'bmr': round(bmr),
        'rmr': round(rmr),
        'tdee': round(tdee),
        'RECOMMEND CALORIE INTAKE': round(recommend_tdee_calorie)
    }


def dynamic_weight_change(formula, gender, weight, height, age, activity_level, calories_intake, days, fitness_goal):
    if formula == "BMR formula : The Harris-Benedict Equation (revised by Roza and Shizgal in 1984)":
        bmr = calculate_bmr(gender, weight, height, age)
        tdee = calculate_tdee(bmr, activity_level)
    elif formula == "RMR formula : Pavlidou (Proposed New Equations), in kcal/d (2022)":
        if gender == "male":
            rmr = (9.65 * weight + 5.73 * height) - 5.08 * age + 260
        else:
            rmr = (7.38 * weight + 6.07 * height) - 2.31 * age + 43
        tdee = calculate_tdee(rmr, activity_level)
    elif formula == "BMR formula :Mifflin-St. Jeor in 1990":
        if gender == "male":
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        tdee = calculate_tdee(bmr, activity_level)
    else:
        raise ValueError("Invalid formula provided.")

    weight_changes = []

    for day in range(days):
        bmi = (height / 100) ** 2
        if bmi > 30:
            metabolic_adaptation = 0.9
        else:
            metabolic_adaptation = 1.0
        adjusted_tdee = tdee * metabolic_adaptation
        daily_energy_deficit = calories_intake - adjusted_tdee
        weight_change = daily_energy_deficit / 7700
        print(weight_change)
        weight += weight_change

        weight_changes.append(weight)

    return weight_changes[-1]


def calculate_ffm(fm, gender):
    if fm <= 0:
        fm = 0.1
    if gender == 'male':
        return 13.8 * math.log(fm) + 16.9
    else:
        return 10.4 * math.log(fm) + 14.2


def calculate_weight_change(tdee, days, initial_fat_mass, total_calories, gender, weight, height, age):
    daily_energy_deficit = (total_calories - tdee)  # energy deficit
    total_energy_deficit = daily_energy_deficit * int(days)

    energy_density_fat = 7700

    change_in_fat_mass = total_energy_deficit / energy_density_fat
    if daily_energy_deficit > 0:
        new_weight = weight + change_in_fat_mass
        return new_weight
    else:
        new_fat_mass = initial_fat_mass - abs(change_in_fat_mass)
        if new_fat_mass < 0:
            new_fat_mass = 0.1
        new_ffm = calculate_ffm(new_fat_mass, gender)
        new_weight = new_fat_mass + new_ffm

    return new_weight


current_dir = os.path.dirname(__file__)
model_path = os.path.join(current_dir, "fine_tuned_model")


@app.route('/DietJournal', methods=['GET', 'POST'])
def diet_journal():
    hidden_fitness_goal = session.get("fitness_goal")
    formula = session.get('BmrRmr')
    gender = session.get('gender')
    weight = session.get('weight')
    height = session.get('height')
    age = session.get('age')
    activity_level = session.get('activity_level')

    nutrients = calculate_nutrients(formula, gender, weight, height, age, activity_level, hidden_fitness_goal)

    carbs = nutrients.get('carbs')
    protein = nutrients.get('protein')
    fat = nutrients.get('fat')

    session['carbs'] = carbs
    session['protein'] = protein
    session['fat'] = fat

    print(f"carbs : {carbs} fat : {fat} protein {protein}")
    dataset_diet = os.path.join(current_dir, "epi_r.csv")
    data_diet = pd.read_csv(dataset_diet, encoding='unicode_escape')
    form = UploadPicturesForm()
    recommends = pd.DataFrame()

    data_diet['calories'] = pd.to_numeric(data_diet['calories'], errors='coerce')
    data_diet['protein'] = pd.to_numeric(data_diet['protein'], errors='coerce')
    data_diet['fat'] = pd.to_numeric(data_diet['fat'], errors='coerce')
    data_diet['carbs'] = data_diet['calories'] - data_diet['protein'] * 4 - data_diet['fat'] * 9
    print(data_diet)
    if hidden_fitness_goal == 'lose':
        selected_foods = data_diet[
            (data_diet['carbs'] <= carbs) & (data_diet['protein'] <= protein) & (data_diet['fat'] <= fat)]
        recommends = selected_foods.sample(n=5)
        print(recommends)
        recommends_recipe = recommends[['title', 'calories', 'protein', 'fat', 'carbs']]
        recommends_dict = recommends_recipe.to_dict(orient='records')
        if 'recommends_dict' not in session:
            session['recommends'] = recommends_dict

    elif hidden_fitness_goal == 'gain':
        selected_foods = data_diet[
            (data_diet['carbs'] >= carbs) & (data_diet['protein'] >= protein) & (data_diet['fat'] >= fat)]
        recommends = selected_foods.sample(n=5)
        print(recommends)
        recommends_recipe = recommends[['title', 'calories', 'protein', 'fat', 'carbs']]
        recommends_dict = recommends_recipe.to_dict(orient='records')
        if 'recommends_dict' not in session:
            session['recommends'] = recommends_dict

    return render_template('Diet Journal.html', form=form, hidden_fitness_goal=hidden_fitness_goal,
                           recommends=session['recommends'], total_carbs=session.get('total_carbs', 0),
                           total_protein=session.get('total_protein', 0),
                           total_fat=session.get('total_fat', 0), carbs=session.get('carbs', 0),
                           protein=session.get('protein', 0),
                           fat=session.get('fat', 0))


@app.route('/delete_product', methods=['POST'])
def delete_product():
    product_index = request.form.get('product_BreakfastIndex')
    product_index1 = request.form.get('product_LunchIndex')
    product_index2 = request.form.get('product_DinnerIndex')
    print(product_index)
    if product_index is not None:
        product_index = int(product_index)
        products_breakfast = session.get('products_breakfast', [])
        print(products_breakfast)  # 0

        print(
            len(products_breakfast))
        if 0 <= product_index < len(products_breakfast):
            products_breakfast.pop(product_index)
            session[
                'products_breakfast'] = products_breakfast

    if product_index1 is not None:
        product_index1 = int(product_index1)
        products_lunch = session.get('products_lunch', [])

        print(
            len(products_lunch))
        if 0 <= product_index1 < len(products_lunch):
            products_lunch.pop(product_index1)
            session[
                'products_lunch'] = products_lunch
    if product_index2 is not None:
        product_index2 = int(product_index2)
        products_dinner = session.get('products_dinner', [])

        print(
            len(products_dinner))
        if 0 <= product_index2 < len(products_dinner):
            products_dinner.pop(product_index2)
            session[
                'products_dinner'] = products_dinner
    update_totals()

    return redirect(url_for('diet_journal'))


def update_totals():
    total_carbs = total_protein = total_fat = 0
    for meal in ['products_breakfast', 'products_lunch', 'products_dinner']:
        for product in session.get(meal, []):
            total_carbs += product.get('carbohydrates', 0)
            total_protein += product.get('protein', 0)
            total_fat += product.get('fat', 0)
    session['total_carbs'] = total_carbs
    session['total_protein'] = total_protein
    session['total_fat'] = total_fat


@app.route('/save_food_log', methods=['POST'])
def save_food_log():
    user = current_user
    if not user:
        user = User.query.filter_by(username=session['username']).first()

    today = datetime.today().date()

    try:
        for product in session.get('products_breakfast', []):
            food_log = FoodLog(user_id=user.user_id, date=today, meal_type='breakfast',
                               food_name=product['product_name'], carbohydrates=product['carbohydrates'],
                               protein=product['protein'], fat=product['fat'],
                               total_carbs=session.get('total_carbs', 0),
                               total_protein=session.get('total_protein', 0),
                               total_fat=session.get('total_fat', 0))
            db.session.add(food_log)

        for product in session.get('products_lunch', []):
            food_log = FoodLog(user_id=user.user_id, date=today, meal_type='lunch',
                               food_name=product['product_name'], carbohydrates=product['carbohydrates'],
                               protein=product['protein'], fat=product['fat'],
                               total_carbs=session.get('total_carbs', 0),
                               total_protein=session.get('total_protein', 0),
                               total_fat=session.get('total_fat', 0))
            db.session.add(food_log)

        for product in session.get('products_dinner', []):
            food_log = FoodLog(user_id=user.user_id, date=today, meal_type='dinner',
                               food_name=product['product_name'], carbohydrates=product['carbohydrates'],
                               protein=product['protein'], fat=product['fat'],
                               total_carbs=session.get('total_carbs', 0),
                               total_protein=session.get('total_protein', 0),
                               total_fat=session.get('total_fat', 0))
            db.session.add(food_log)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving food log: {e}")
        return redirect(url_for('diet_journal'))

    return redirect(url_for('history'))


@app.route('/History', methods=['GET', 'POST'])
def history():
    user = current_user
    print(user)
    if not user:
        user = User.query.filter_by(username=session['username']).first()
    print(user)
    user_food_history = FoodLog.query.filter_by(user_id=user.user_id).all()
    food_history_details = []
    for entry in user_food_history:
        food_history_details.append({
            'user_id': entry.user_id,
            'date': entry.date,
            'meal_type': entry.meal_type,
            'food_name': entry.food_name,
            'carbohydrates': entry.carbohydrates,
            'protein': entry.protein,
            'fat': entry.fat,
        })

    return render_template("FoodHistory.html", food_history_details=food_history_details)


@app.route('/Upload_Barcode', methods=['GET', 'POST'])
def upload_barcode():
    form = UploadPicturesForm()
    if form.validate_on_submit():
        if form.picture_file.data:
            unique_str = str(uuid4())
            filename = secure_filename(f'{unique_str}-{form.picture_file.data.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.picture_file.data.save(filepath)
            image = Image.open(filepath)
            barcodes = decode(image)
            results = []
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                results.append({'type': barcode_type, 'data': barcode_data})

                meal = request.form.get('meal')
                if meal == 'breakfast':
                    session['results_breakfast'] = results
                elif meal == 'lunch':
                    session['results_lunch'] = results
                elif meal == 'dinner':
                    session['results_dinner'] = results
                else:
                    return redirect(url_for('diet_journal'))
    return render_template('Diet Journal.html', form=form, carbs=session.get('carbs', 0),
                           protein=session.get('protein', 0),
                           fat=session.get('fat', 0))


def save_picture(form_picture):
    random_hex = uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    form_picture.save(picture_path)
    return picture_fn


@app.route('/upload_Pictures', methods=['GET', 'POST'])
def upload_pictures():
    form = UploadPicturesForm()
    if form.validate_on_submit():
        if form.picture_file.data:
            unique_str = str(uuid4())
            filename = secure_filename(f'{unique_str}-{form.picture_file.data.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.picture_file.data.save(filepath)
            db.session.commit()
            flash(f"New user has Uploaded", category="success")

        return redirect(url_for("index"))

    return render_template("uploads_user.html", form=form)


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account_status():
    form = UpdateForm()

    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data

        if form.password.data:
            current_user.password_hash = generate_password_hash(form.password.data, salt_length=32)
        try:
            db.session.commit()
            flash('Your ac  count has been updated!', 'success')
        except:
            db.session.rollback()
            if User.query.filter_by(username=form.username.data):
                form.username.errors.append('This username is already taken. Please choose another')
            if User.query.filter_by(email=form.email.data):
                form.email.errors.append('This email address is already registered. Please choose another')
            flash('Account update failed', 'danger')
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', form=form, image_file=image_file)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # if user is None or not user.check_password(form.password.data):
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)

        flash(f'Login for {form.username.data}', 'success')

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)


app.secret_key = 'random_secret_key'
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id='334365192133-me4ac8egu7o7fud5k6849k3p54repusk.apps.googleusercontent.com',
    client_secret='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',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
)


@app.route('/login_Google', methods=['GET', 'POST'])
def login_Google():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/login/callback')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    session['google_user'] = {
        'email': user_info['email'],
        'name': user_info.get('name'),
        'picture': user_info.get('picture')
    }
    user = User.query.filter_by(email=user_info['email']).first()
    if user is None:
        dummy_password_hash = generate_password_hash('default_password')
        user = User(username=user_info.get('name'), email=user_info['email'],
                    password_hash=dummy_password_hash)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    session['username'] = user.username
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    session.pop('user_id', None)  # session.clear() may cause some issues so use pop will be safe
    session.pop('token', None)
    session.pop('total_carbs', None)
    session.pop('total_fat', None)
    session.pop('total_protein', None)
    session.pop('products_breakfast', None)
    session.pop('products_lunch', None)
    session.pop('products_dinner', None)
    return redirect(url_for('index'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if form.password.data == form.confirmpassword.data:
                hash_password = generate_password_hash(form.password.data)
                user.password_hash = hash_password
                db.session.commit()
        flash(f'Change for {form.username.data} Success', 'success')
        return redirect(url_for('index'))
    return render_template('forgot_password.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            try:
                hash_password = generate_password_hash(form.password.data)
                user1 = User(username=form.username.data, email=form.email.data, password_hash=hash_password)
                db.session.add(user1)
                db.session.commit()
                flash(f'Registration for {form.username.data} received', 'success')
                return redirect(url_for('index'))
            except IntegrityError:
                db.session.rollback()
                flash('An error occurred. The username might already be taken. Please try a different one.', 'danger')
    return render_template('registration.html', title='Register', form=form)


def is_valid_email(email):
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as error:
        return False
    return True


# Attempt to remove a file but silently cancel any exceptions if anything goes wrong
def silent_remove(filepath):
    try:
        os.remove(filepath)
    except:
        pass
    return


@app.route('/barcode', methods=['GET', 'POST'])
@login_required
def barcode_scan():
    return render_template('barcode.html')


@app.route('/searchITEM', methods=['POST'])
def get_food_data():
    form = UploadPicturesForm()

    products_breakfast = []
    products_lunch = []
    products_dinner = []

    if request.method == 'POST':
        if request.form.get("barcode_breakfast"):
            new_products_breakfast = search_food(request.form.get("barcode_breakfast"))
            if 'products_breakfast' in session:
                session['products_breakfast'] += new_products_breakfast
            else:
                session['products_breakfast'] = new_products_breakfast
        if request.form.get("barcode_lunch"):
            new_products_lunch = search_food(request.form.get("barcode_lunch"))
            if 'products_lunch' in session:
                session['products_lunch'] += new_products_lunch
            else:
                session['products_lunch'] = new_products_lunch
        if request.form.get("barcode_dinner"):
            new_products_dinner = search_food(request.form.get("barcode_dinner"))
            if 'products_dinner' in session:
                session['products_dinner'] += new_products_dinner
            else:
                session['products_dinner'] = new_products_dinner

        total_carbs = 0
        total_fat = 0
        total_protein = 0
        for carbon_breakfast in session.get("products_breakfast", []):
            total_carbs += carbon_breakfast.get('carbohydrates', 0)
        for carbon_lunch in session.get("products_lunch", []):
            total_carbs += carbon_lunch.get("carbohydrates", 0)
        for carbon_dinner in session.get("products_dinner", []):
            total_carbs += carbon_dinner.get("carbohydrates", 0)
        session["total_carbs"] = total_carbs
        # EXAMPLE

        # session {
        #     "products_breakfast": [
        #         {
        #             "product_name": "Nutella",
        #             "carbohydrates": 57.5,
        #             "fat": 30.9,
        #             "protein": 6.3
        #         },
        #         {
        #             "product_name": "Cornflakes",
        #             "carbohydrates": 84,
        #             "fat": 1,
        #             "protein": 8
        #         }
        #     ],
        #     "products_lunch": [
        #         {
        #             "product_name": "Chicken Sandwich",
        #             "carbohydrates": 30,
        #             "fat": 10,
        #             "protein": 25
        #         }
        #     ],
        #     "products_dinner": [
        #         {
        #             "product_name": "Spaghetti",
        #             "carbohydrates": 75,
        #             "fat": 10,
        #             "protein": 12
        #         }
        #     ],
        #     "total_carbs": 246
        # }

        for protein_breakfast in session.get("products_breakfast", []):
            total_protein += protein_breakfast.get("protein", 0)
        for protein_lunch in session.get("products_lunch", []):
            total_protein += protein_lunch.get("protein", 0)
        for protein_dinner in session.get("products_dinner", []):
            total_protein += protein_dinner.get("protein", 0)
        session["total_protein"] = total_protein

        for fat_breakfast in session.get("products_breakfast", []):
            total_fat += fat_breakfast.get("fat", 0)
        for fat_lunch in session.get("products_lunch", []):
            total_fat += fat_lunch.get("fat", 0)
        for fat_dinner in session.get("products_dinner", []):
            total_fat += fat_dinner.get("fat", 0)
        session["total_fat"] = total_fat

        return render_template('Diet Journal.html', products_breakfast=products_breakfast,
                               products_lunch=products_lunch,
                               products_dinner=products_dinner,
                               total_carbs=total_carbs,
                               total_protein=total_protein,
                               total_fat=total_fat, form=form, recommends=session.get('recommends', []),
                               )


def search_food(barcode):
    response = requests.get(f"https://world.openfoodfacts.org/api/v3/product/{barcode}.json")
    if response.status_code == 200:
        try:
            product_data = response.json()['product']
            # "code": "3017624010701",
            # "product": {

            # "product_name" : {"Nutella"},
            #     "nutriments": {
            #         "carbohydrates": 57.5,
            #         "carbohydrates_100g": 57.5,
            #         "carbohydrates_unit": "g",
            #         "carbohydrates_value": 57.5,
            #         "energy": 2255,
            #         "energy-kcal": 539,
            #         "energy-kcal_100g": 539,
            #         "energy-kcal_unit": "kcal",
            #         ...,
            #         ...,
            #         "sugars": 56.3,
            #         "sugars_100g": 56.3,
            #         "sugars_unit": "g",
            #         "sugars_value": 56.3
            #     },

            product_info = {
                'product_name': product_data.get('product_name', 'unknown'),
                'carbohydrates': product_data['nutriments'].get('carbohydrates', 'unknown'),
                'fat': product_data['nutriments'].get('fat', 'unknown'),
                'protein': product_data['nutriments'].get('proteins', 'unknown')
            }
            return [product_info]
        except ValueError:
            print("No JSON data returned")
    else:
        print(f"Error fetching data: HTTP {response.status_code}")
    return []


@app.route('/Choose', methods=['GET', 'POST'])
def choose():
    if request.method == 'POST':
        index_Breakfast = request.form.get("Choose")
        index_Lunch = request.form.get("barcode_Lunch")
        index_Dinner = request.form.get("barcode_Dinner")

        product_name_Breakfast = request.form.get(f"product_name_{index_Breakfast}")
        product_name_Lunch = request.form.get(f"product_name_{index_Lunch}")
        product_name_Dinner = request.form.get(f"product_name_{index_Dinner}")

        carbohydrates_Breakfast = float(request.form.get(f"carbohydrates_{index_Breakfast}", 0))
        fat_Breakfast = float(request.form.get(f"fat_{index_Breakfast}", 0))
        protein_Breakfast = float(request.form.get(f"protein_{index_Breakfast}", 0))

        carbohydrates_Lunch = float(request.form.get(f"carbohydrates_{index_Lunch}", 0))
        fat_Lunch = float(request.form.get(f"fat_{index_Lunch}", 0))
        protein_Lunch = float(request.form.get(f"protein_{index_Lunch}", 0))

        carbohydrates_Dinner = float(request.form.get(f"carbohydrates_{index_Dinner}", 0))
        fat_Dinner = float(request.form.get(f"fat_{index_Dinner}", 0))
        protein_Dinner = float(request.form.get(f"protein_{index_Dinner}", 0))

        session['total_carbs'] = session.get('total_carbs',
                                             0) + carbohydrates_Breakfast + carbohydrates_Lunch + carbohydrates_Dinner
        session['total_fat'] = session.get('total_fat', 0) + fat_Breakfast + fat_Lunch + fat_Dinner
        session['total_protein'] = session.get('total_protein', 0) + protein_Breakfast + protein_Lunch + protein_Dinner

        if product_name_Breakfast:
            session['last_product'] = product_name_Breakfast
        elif product_name_Lunch:
            session['last_product'] = product_name_Lunch
        elif product_name_Dinner:
            session['last_product'] = product_name_Dinner

    return render_template('Diet Journal.html',
                           product_name_Breakfast=product_name_Breakfast,
                           carbohydrates_Breakfast=carbohydrates_Breakfast,
                           fat_Breakfast=fat_Breakfast,
                           protein_Breakfast=protein_Breakfast,
                           product_name_Lunch=product_name_Lunch,
                           carbohydrates_Lunch=carbohydrates_Lunch,
                           fat_Lunch=fat_Lunch,
                           protein_Lunch=protein_Lunch,
                           product_name_Dinner=product_name_Dinner,
                           carbohydrates_Dinner=carbohydrates_Dinner,
                           fat_Dinner=fat_Dinner,
                           protein_Dinner=protein_Dinner,
                           total_carbs=session.get('total_carbs', 0),
                           total_fat=session.get('total_fat', 0),
                           total_protein=session.get('total_protein', 0))


@app.route('/search_ProductName', methods=['GET', 'POST'])
@login_required
def search_ProductName():
    return render_template('search_Product.html')


@app.route('/search_Product', methods=['GET', 'POST'])
def search_product():
    search_query = request.form.get("product_name")
    print(search_query)
    response = requests.get(
        f"https://world.openfoodfacts.net/api/v2/search?search_terms={search_query}&fields=product_name,nutriscore_data,nutriments,nutrition_grades")
    print(response.status_code)
    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:
            print("No JSON data returned")
            data = {}
    else:
        print(f"Error fetching data: HTTP {response.status_code}")
        data = {}

    products = []
    if 'products' in data:
        for product in data['products']:
            product_info = {
                'product_name': product.get('product_name', 'unknown'),
                'carbohydrates': product['nutriments'].get('carbohydrates', 'unknown'),
                'fat': product['nutriments'].get('fat', 'unknown'),
                'protein': product['nutriments'].get('proteins', 'unknown')
            }
            products.append(product_info)

        return render_template('search_item.html', products=products)
    return render_template('search_item.html', products=[])


@app.route('/nearby_gyms', methods=['GET'])
def nearby_gyms():
    google_maps_api_key = "AIzaSyDAb5nxW_WUizlEfUrhgkiX92J5JnMCQuI"  # Google API Key
    return render_template('GoogleMaps.html', google_maps_api_key=google_maps_api_key)


system_message = """you are an healthy assistant help people to make their life better.
people who wants to lose weight give them some tips or people who wants to gain weight give them some tips. 
people who wants to gain some healthy knowledge give them some advice.
people who is struggling with not lose weight enough or gian weight enough give them some emotional support.
""".strip().replace('\n', '')

client = GroqChatClient(model_id="llama3-8b-8192", system_message=system_message)


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    response = client.send_request(client.draft_message(user_input), stream=False)
    return jsonify({'answer': response['content']})


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.errorhandler(413)
def error_413(error):
    return render_template("errors/413.html"), 413
