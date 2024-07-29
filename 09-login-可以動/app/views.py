import csv
import json
import math
import os
from datetime import datetime
from uuid import uuid4
from PIL import Image
from pyzbar.pyzbar import decode
import numpy as np
from sklearn.linear_model import SGDRegressor, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import requests
from email_validator import validate_email, EmailNotValidError
from flask import render_template, redirect, url_for, flash, request, jsonify, logging, session, Response
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from werkzeug.utils import secure_filename
import cv2
from pyzbar import pyzbar
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
@app.route('/index')  # URL：這是網站的地址或特定網頁的路徑，通常顯示在瀏覽器的地址欄中。
@login_required
def index():  # 路由函數，路由函數是一段 Python 代碼，用於處理對特定 URL 的訪問請求。
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
        gender = request.form['gender']
        weight = float(request.form['weight'])
        session['weight'] = weight
        height = float(request.form['height'])
        session['height'] = height
        age = int(request.form['age'])
        session['age'] = age
        activity_level = request.form['activity_level']
        # 儘管在 HTML 表單中您定義的選項值是數字（如 "1.2"），但當這些數據通過表單提交到後端時，它們仍然會被處理為字符串。
        days = request.form['days']
        fitness_goal = request.form['fitness_goal']
        print(fitness_goal)
        session['fitness_goal'] = fitness_goal
        session['BmrRmr'] = formula
        session['gender'] = gender
        session['weight'] = weight
        session['height'] = height
        session['age'] = age
        session['activity_level'] = activity_level
        session['days'] = days
        nutrients = calculate_nutrients(formula, gender, weight, height, age, activity_level, fitness_goal)
        # 假設初步的脂肪質量和無脂肪質量，這些值通常需要更精確的測量或估計
        initial_fat_mass = weight * 0.25  # 脂肪
        # initial_ffm = weight * 0.75  # 無脂肪是肌肉跟、骨骼、水分、器官等。
        new_weight = calculate_weight_change(nutrients['tdee'], days, initial_fat_mass,
                                             nutrients['calories'], gender, weight, height, age)

    # 使用這個函數來計算預測的體重變化

    return render_template('index.html', nutrients=nutrients, days=days, new_weight=new_weight,
                           )


def calculate_nutrients(formula, gender, weight, height, age, activity_level, fitness_goal):
    # Calculate BMR or RMR
    bmr = 0
    rmr = 0
    tdee = 0
    if formula == "BMR formula : The Harris-Benedict Equation (revised by Roza and Shizgal in 1984":
        if gender == "male":
            bmr = 88.362 + (weight * 13.397) + (height * 4.799) - (age * 5.677)
        else:
            bmr = 447.593 + (weight * 9.247) + (height * 3.098) - (age * 4.330)

    if formula == "RMR formula : Pavlidou (Proposed New Equations), in kcal/d (2022)":

        if gender == "male":
            rmr = (9.65 * weight + 5.73 * height) - 5.08 * age + 260
        else:
            rmr = (7.38 * weight + 6.07 * height) - 2.31 * age + 43

    # Total daily energy expenditure
    if bmr > 0:
        tdee = bmr * float(activity_level)
    else:
        bmr = 0
    if rmr > 0:
        tdee = rmr * float(activity_level)
    else:
        rmr = 0
    print(f"tdee : {tdee}")
    # Total calories over the period

    # Adjust total calories based on fitness goal
    if fitness_goal == "gain":
        recommend_tdee_calrie = tdee + 300  # increase 300 grams for 能量缺口
        print(f"recommend : {recommend_tdee_calrie}")
        # 碳水化合物是人體主要的能量來源，通常建議佔每日總熱量的 45% 至 65%。這裡的 56% 是一個中間值，符合大多數健康飲食指南。
        protein = weight * 1.2
        # 通常建議蛋白質佔每日總熱量的 10% 至 35%。
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        # 一般建議脂肪佔每日總熱量的 20% 至 35%。這裡的 29% 同樣是一個中間值，符合多數健康飲食的建議範圍。
        carbs_percent = (recommend_tdee_calrie - protein * 4 - fat * 9) / recommend_tdee_calrie  # 4 calories per gram
        carbs = (recommend_tdee_calrie * carbs_percent) / 4
    elif fitness_goal == "lose":
        # total_calories_perday = tdee * 0.85  # 減少 15% 的熱量以助於減脂
        recommend_tdee_calrie = tdee - 300  # decrease 300 grams for 能量缺口

        # 碳水化合物是人體主要的能量來源，通常建議佔每日總熱量的 45% 至 65%。這裡的 50% 是一個中間值，符合大多數健康飲食指南。
        protein = weight * 1.2
        # 通常建議蛋白質佔每日總熱量的 10% 至 35%。
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        carbs_percent = (recommend_tdee_calrie - protein * 4 - fat * 9) / recommend_tdee_calrie  # 4 calories per gram
        carbs = (recommend_tdee_calrie * carbs_percent) / 4  # 4 calories per gram
        # 一般建議脂肪佔每日總熱量的 20% 至 35%。這裡的 30% 同樣是一個中間值，符合多數健康飲食的建議範圍。
    else:  # "maintain"
        recommend_tdee_calrie = tdee  # 維持目前的熱量攝入
        # Nutrient breakdown
        # 碳水化合物是人體主要的能量來源，通常建議佔每日總熱量的 45% 至 65%。這裡的 50% 是一個中間值，符合大多數健康飲食指南。
        protein = weight * 1.2
        # 通常建議蛋白質佔每日總熱量的 10% 至 35%。
        fat = (tdee * 0.25) / 9  # 9 calories per gram
        # 一般建議脂肪佔每日總熱量的 20% 至 35%。這裡的 30% 同樣是一個中間值，符合多數健康飲食的建議範圍。
        carbs_percent = (recommend_tdee_calrie - protein * 4 - fat * 9) / recommend_tdee_calrie  # 4 calories per gram
        carbs = (recommend_tdee_calrie * carbs_percent) / 4  # 4 calories per gram
    print(recommend_tdee_calrie)
    print(tdee)
    return {
        'calories': round(recommend_tdee_calrie),  # round 對數字進行四捨五入處理
        'carbs': round(carbs),
        'protein': round(protein),
        'fat': round(fat),
        'bmr': round(bmr),
        'rmr': round(rmr),
        'tdee': round(tdee),
        'RECOMMEND CALORIE INTAKE': round(recommend_tdee_calrie)
    }


# 在體重減少的過程中，身體會首先動員脂肪儲備來提供能量，因此脂肪質量通常會減少。
# 反之，在體重增加的過程中，多餘的能量會以脂肪形式儲存，導致脂肪質量增加。
# 體重變化影響：在體重減少的過程中，如果能量攝入不足，身體不僅會消耗脂肪，還可能分解肌肉組織以獲得額外能量，導致非脂肪質量(肌肉)下降。
# 而在增重過程中，適當的訓練和營養攝入可以增加肌肉質量，而不是 脂肪質量。
# 福布斯模型說明 FM -> 所有脂肪的總和，FFM -> 肌肉、骨骼、水分、器官
# 假設一個人開始減肥計畫，他的體重從80公斤減到70公斤。
# 根據 Forbes 模型，我們可以預測他在這10公斤減重中，可能會減少7公斤的脂肪（FM），以及3公斤的非脂肪質量（FFM）。
# 這些數據可以幫助我們了解他的減重過程是否健康和有效，並且可以用來調整他的飲食和運動計劃，以保護他的肌肉質量和健康。
def calculate_ffm(fm, gender):
    # 確保傳入的脂肪質量大於零，避免數學錯誤
    if fm <= 0:
        fm = 0.1  # 避免對數計算錯誤，給一個非零的最小值
    if gender == 'male':
        return 13.8 * math.log(fm) + 16.9  # 男性的福布斯方程式
    else:
        return 10.4 * math.log(fm) + 14.2  # 女性的福布斯方程式


def calculate_weight_change(tdee, days, initial_fat_mass, total_calories, gender, weight, height, age):
    daily_energy_deficit = (total_calories - tdee)  # 計算能量缺口
    total_energy_deficit = daily_energy_deficit * int(days)

    energy_density_fat = 7700  # 每公斤脂肪約7700千卡

    # 計算脂肪質量和無脂肪質量的變化
    change_in_fat_mass = total_energy_deficit / energy_density_fat
    if daily_energy_deficit > 0:  # 增重情況
        new_weight = weight + change_in_fat_mass
        return new_weight
    else:  # 減重情況
        new_fat_mass = initial_fat_mass - abs(change_in_fat_mass)
    print(new_fat_mass)
    new_ffm = calculate_ffm(new_fat_mass, gender)  # 使用福布斯方程式計算新的無脂肪質量
    print(new_ffm)
    new_weight = new_fat_mass + new_ffm
    return new_weight


# 获取当前脚本所在目录
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

    carbs = nutrients['carbs']
    protein = nutrients['protein']
    fat = nutrients['fat']

    dataset_diet = os.path.join(current_dir, "epi_r.csv")
    data_diet = pd.read_csv(dataset_diet, encoding='unicode_escape')
    form = UploadPicturesForm()
    recommends = pd.DataFrame()
    # 将 'calories'、'protein' 和 'fat' 列转换为数值类型

    data_diet['calories'] = pd.to_numeric(data_diet['calories'], errors='coerce')
    data_diet['protein'] = pd.to_numeric(data_diet['protein'], errors='coerce')
    data_diet['fat'] = pd.to_numeric(data_diet['fat'], errors='coerce')
    # Calculate carbs
    data_diet['carbs'] = data_diet['calories'] - data_diet['protein'] * 4 - data_diet['fat'] * 9
    print(data_diet)
    if hidden_fitness_goal == 'lose':
        selected_foods = data_diet[
            (data_diet['carbs'] <= carbs) & (data_diet['protein'] <= protein) & (data_diet['fat'] <= fat)]
        recommends = selected_foods.sample(n=5)  # 透過 pandas 的隨機篩選 5 個資料回去
        print(recommends)
        recommends_recipe = recommends[['title', 'calories', 'protein', 'fat', 'carbs']]
        recommends_dict = recommends_recipe.to_dict(orient='records')
        if 'recommends_dict' not in session:
            session['recommends'] = recommends_dict

    elif hidden_fitness_goal == 'gain':
        selected_foods = data_diet[
            (data_diet['carbs'] >= carbs) & (data_diet['protein'] >= protein) & (data_diet['fat'] >= fat)]
        recommends = selected_foods.sample(n=5)  # 透過 pandas 的隨機篩選 5 個資料回去
        print(recommends)
        recommends_recipe = recommends[['title', 'calories', 'protein', 'fat', 'carbs']]
        recommends_dict = recommends_recipe.to_dict(orient='records')
        if 'recommends_dict' not in session:
            session['recommends'] = recommends_dict

    return render_template('Diet Journal.html', form=form, hidden_fitness_goal=hidden_fitness_goal,
                           recommends=session['recommends'], total_carbs=session.get('total_carbs', 0),
                           total_protein=session.get('total_protein', 0),
                           total_fat=session.get('total_fat', 0))


@app.route('/delete_product', methods=['POST'])
def delete_product():
    product_index = request.form.get('product_BreakfastIndex')
    product_index1 = request.form.get('product_LunchIndex')
    product_index2 = request.form.get('product_DinnerIndex')
    print(product_index)
    if product_index is not None:
        product_index = int(product_index)  # 將索引轉換為整數
        products_breakfast = session.get('products_breakfast', [])
        print(products_breakfast)  # 0
        # session.get('products_breakfast', [])  從 session 中獲取名為 products_breakfast 的產品列表。如果
        # session 中沒有這個鍵，它會返回一個空的列表[]。
        print(
            len(products_breakfast))  # [{'carbohydrates': 9.5, 'fat': 0.5, 'product_name': 'Strawberry Banana Smoothie', 'protein': 0.5}]
        # list 中只有 1 個資料
        if 0 <= product_index < len(products_breakfast):
            products_breakfast.pop(product_index)
            session[
                'products_breakfast'] = products_breakfast  # # 例如，在這個例子中，用戶刪除了早餐產品列表中的一項產品，我們需要將這個變更保存到會話中，以便在後續的請求中反映最新的列表狀態。

            # ex :
            # session = {
            #     'products_breakfast': [
            #         {'product_name': 'Eggs', 'carbohydrates': 1, 'fat': 5, 'protein': 6},
            #         {'product_name': 'Bacon', 'carbohydrates': 0, 'fat': 42, 'protein': 37},
            #         {'product_name': 'Toast', 'carbohydrates': 12, 'fat': 2, 'protein': 3}
            #     ]
            # }

        # products_breakfast.pop(1)  index = 1  刪除 也就是第 1 行的要刪除

        # products_breakfast = [
        #     {'product_name': 'Eggs', 'carbohydrates': 1, 'fat': 5, 'protein': 6},
        #     {'product_name': 'Toast', 'carbohydrates': 12, 'fat': 2, 'protein': 3}
        # ]

        # 更新會話數據：
        # session['products_breakfast'] = products_breakfast
    if product_index1 is not None:
        product_index1 = int(product_index1)  # 將索引轉換為整數
        products_lunch = session.get('products_lunch', [])
        # session.get('products_breakfast', [])  從 session 中獲取名為 products_breakfast 的產品列表。如果
        # session 中沒有這個鍵，它會返回一個空的列表[]。
        print(
            len(products_lunch))  # [{'carbohydrates': 9.5, 'fat': 0.5, 'product_name': 'Strawberry Banana Smoothie', 'protein': 0.5}]
        # list 中只有 1 個資料
        if 0 <= product_index1 < len(products_lunch):
            products_lunch.pop(product_index1)
            session[
                'products_lunch'] = products_lunch  # # 例如，在這個例子中，用戶刪除了早餐產品列表中的一項產品，我們需要將這個變更保存到會話中，以便在後續的請求中反映最新的列表狀態。

    if product_index2 is not None:
        product_index2 = int(product_index2)  # 將索引轉換為整數
        products_dinner = session.get('products_dinner', [])
        # session.get('products_breakfast', [])  從 session 中獲取名為 products_breakfast 的產品列表。如果
        # session 中沒有這個鍵，它會返回一個空的列表[]。
        print(
            len(products_dinner))  # [{'carbohydrates': 9.5, 'fat': 0.5, 'product_name': 'Strawberry Banana Smoothie', 'protein': 0.5}]
        # list 中只有 1 個資料
        if 0 <= product_index2 < len(products_dinner):
            products_dinner.pop(product_index2)
            session[
                'products_dinner'] = products_dinner  # # 例如，在這個例子中，用戶刪除了早餐產品列表中的一項產品，我們需要將這個變更保存到會話中，以便在後續的請求中反映最新的列表狀態。

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
        # save breakfast data
        for product in session.get('products_breakfast', []):
            food_log = FoodLog(user_id=user.user_id, date=today, meal_type='breakfast',
                               food_name=product['product_name'], carbohydrates=product['carbohydrates'],
                               protein=product['protein'], fat=product['fat'],
                               total_carbs=session.get('total_carbs', 0),
                               total_protein=session.get('total_protein', 0),
                               total_fat=session.get('total_fat', 0))
            db.session.add(food_log)

        # save lunch data
        for product in session.get('products_lunch', []):
            food_log = FoodLog(user_id=user.user_id, date=today, meal_type='lunch',
                               food_name=product['product_name'], carbohydrates=product['carbohydrates'],
                               protein=product['protein'], fat=product['fat'],
                               total_carbs=session.get('total_carbs', 0),
                               total_protein=session.get('total_protein', 0),
                               total_fat=session.get('total_fat', 0))
            db.session.add(food_log)

        # save dinner data
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
    # user_food_history = FoodLog.query.filter_by(user_id=user.user_id).all()
    user_food_history = FoodLog.query.filter_by(user_id=user.user_id).all()
    # 假設 FoodLog 有 date 和 food_item 欄位
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

    # 這裡假設你要在終端機上顯示這些資料
    # for detail in food_history_details:
    #     print(f"日期: {detail['date']}, 食物name: {detail['food_name']}")

    return render_template("FoodHistory.html",food_history_details=food_history_details)

@app.route('/Upload_Barcode', methods=['GET', 'POST'])
def upload_barcode():
    form = UploadPicturesForm()
    if form.validate_on_submit():
        if form.picture_file.data:
            unique_str = str(uuid4())
            filename = secure_filename(f'{unique_str}-{form.picture_file.data.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.picture_file.data.save(filepath)  # 儲存起來
            image = Image.open(filepath)
            barcodes = decode(image)
            results = []
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                results.append({'type': barcode_type, 'data': barcode_data})

                # 根據提交的表單區分不同的餐段
                meal = request.form.get('meal')
                if meal == 'breakfast':
                    session['results_breakfast'] = results
                elif meal == 'lunch':
                    session['results_lunch'] = results
                elif meal == 'dinner':
                    session['results_dinner'] = results
                else:
                    return redirect(url_for('diet_journal'))
    return render_template('Diet Journal.html', form=form)


def save_picture(form_picture):
    random_hex = uuid4().hex  # 這行代碼使用 uuid 模塊生成一個隨機的唯一識別碼（UUID），然後通過 .hex 属性獲取其十六進制的字符串形式。這確保每個上傳的文件都有一個獨特的名稱。
    _, f_ext = os.path.splitext(form_picture.filename)
    # form_picture.filename 是指上傳的圖片的原始文件名，例如 "avatar.jpg"。
    # os.path.splitext(form_picture.filename) 會返回一個元組
    # 例如 ('avatar', '.jpg')，這裡 'avatar' 是文件的基本名稱，而 '.jpg' 是文件的擴展名。
    # 使用 _ 這個下劃線作為變數名是一種約定俗成的做法，用來指「這個變數我們不會用到」。在上面的例子中，我們不關心 'profile' 這個基本名稱，所以用 _ 來接收這個值。
    picture_fn = random_hex + f_ext  # 這行代碼將前面生成的隨機十六進制字符串和文件擴展名結合起來，創建一個新的文件名。
    # _ 會接收 "avatar"（我們不使用這個值）。
    # f_ext 會接收 ".jpg"（這是我們需要的擴展名）。
    # 結果，我們只保留了擴展名".jpg"，並將它用於之後生成新的唯一文件名。
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    # 使用 os.path.join() 函數將應用的根路徑（app.root_path）
    # 、存儲靜態個人檔案圖片的目錄（'static/profile_pics'）以及新的文件名（picture_fn）拼接起來，形成文件的完整路徑。
    form_picture.save(picture_path)
    # 實際上將上傳的圖片保存到剛才構建的路徑。
    return picture_fn
    # 函數返回新的文件名
    # 例如，假設有一個來自用戶提交的表單圖片文件，文件名為 "avatar.jpg"。
    # 當這個文件通過 save_picture 函數處理時，將會生成一個隨機的十六進制字符串，比如 "4e5a7b8c9d0e"，然後提取出文件擴展名 ".jpg"
    # 結合這兩部分生成新的文件名 "4e5a7b8c9d0e.jpg"。
    # 接著，這個新文件名會被用來創建完整的路徑，並將文件保存在該路徑下。最終，"4e5a7b8c9d0e.jpg" 這個新文件名將被返回，以供後續使用。


@app.route('/upload_Pictures', methods=['GET', 'POST'])
def upload_pictures():
    form = UploadPicturesForm()
    if form.validate_on_submit():
        if form.picture_file.data:
            unique_str = str(uuid4())
            filename = secure_filename(f'{unique_str}-{form.picture_file.data.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.picture_file.data.save(filepath)  # 儲存起來
            # 要寫進資料庫裏面
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
        # is authenticated：如果使用者提交了有效的密碼，則返回 True
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # if user is None or not user.check_password(form.password.data):
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        # 這一行代碼會在用戶的會話中記錄用戶的登入狀態，選擇性地設置remember_me功能。

        flash(f'Login for {form.username.data}', 'success')

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
        # 假設用戶原本想要去一個叫dashboard的頁面，但是他們需要登入。
        # 他們點擊登入，被帶到登入頁面，網址可能看起來像這樣：/login?next=/dashboard。
        # 用戶輸入資料並提交，登入成功。
        # 登入後，代碼首先查看網址中的next參數，看用戶原本想去哪。
        # 由於next參數是/dashboard，代碼將用戶導向dashboard頁面。
        # 如果沒有next參數，或者next參數是一個外部網站的鏈接，代碼就會忽略它，並把用戶帶到首頁。
        # 所以這段代碼就像是在確認，"你現在登入了，你之前想去哪裡？如果你沒告訴我，或者你告訴我的地方不對，那我就帶你去首頁。"

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
        # 如果用戶不存在，創建一個新的用戶
        dummy_password_hash = generate_password_hash('default_password')
        user = User(username=user_info.get('name'), email=user_info['email'],
                    password_hash=dummy_password_hash)  # 假設允許用戶後續設定 username
        db.session.add(user)
        db.session.commit()

    login_user(user)
    session['username'] = user.username
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    # session.clear()
    session.pop('user_id', None)  # 弄session.clear()會導致無法正常登出，所以把要的東西給拿掉即可
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
        hash_password = generate_password_hash(form.password.data)
        flash(f'Registration for {form.username.data} received', 'success')
        user1 = User(username=form.username.data, email=form.email.data, password_hash=hash_password)
        db.session.add(user1)
        db.session.commit()
        return redirect(url_for('index'))
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
    # 顯示一個表單讓用戶輸入條形碼
    return render_template('barcode.html')


@app.route('/searchITEM', methods=['POST'])
def get_food_data():
    form = UploadPicturesForm()
    # 初始化產品列表
    products_breakfast = []
    products_lunch = []
    products_dinner = []

    if request.method == 'POST':
        if request.form.get("barcode_breakfast"):
            new_products_breakfast = search_food(request.form.get("barcode_breakfast"))
            # 檢查 session 中是否已有早餐食物列表，如果有，則追加新資訊
            if 'products_breakfast' in session:
                # 在 Flask 中，session 是一個像字典一樣的對象，用來存儲跨請求的數據。
                #  因此，當我們使用 'products_breakfast' 這樣的字串來訪問 session 中的資料時，這個字串實際上是作為一個鍵（key）來使用的。
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

        # update_totals()
        # 重新計算總碳水化合物、總脂肪和總蛋白質
        total_carbs = 0
        total_fat = 0
        total_protein = 0
        # session 裡面有 total_carbs 的話就使用有的數值，沒有的話就 = 0
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
                'product_name': product_data.get('product_name', 'unknown'),  # 現在的 product 被存成 product_data，在第1層
                'carbohydrates': product_data['nutriments'].get('carbohydrates', 'unknown'),  # 要娶的是第 2 層的東西
                'fat': product_data['nutriments'].get('fat', 'unknown'),
                'protein': product_data['nutriments'].get('proteins', 'unknown')
            }
            return [product_info]  # 返回產品列表
        except ValueError:
            print("No JSON data returned")
    else:
        print(f"Error fetching data: HTTP {response.status_code}")
    return []


# @app.route('/Choose', methods=['GET', 'POST'])
# def choose():
#     if request.method == 'POST':
#         index_Breakfast = None
#         index_Lunch = None
#         index_Dinner = None
#         product_name_Breakfast = None
#         product_name_Lunch = None
#         product_name_Dinner = None
#         print(123)
#         if request.form.get("Choose"):
#             index_Breakfast = request.form.get("Choose")  # 從表單獲取搜索關鍵字
#             print(index_Breakfast)
#             product_name_Breakfast = request.form.get(f"product_name_{index_Breakfast}")
#             print(product_name_Breakfast)
#         elif request.form.get("barcode_Lunch"):  # 從表單獲取搜索關鍵字
#             index_Lunch = request.form.get("barcode_Lunch")  # 從表單獲取搜索關鍵字
#             product_name_Lunch = request.form.get(f"product_name_{index_Lunch}")
#         else:
#             index_Dinner = request.form.get("barcode_Dinner")  # 從表單獲取搜索關鍵字
#             product_name_Dinner = request.form.get(f"product_name_{index_Dinner}")
#
#         carbohydrates_Breakfast = float(request.form.get(f"carbohydrates_{index_Breakfast}", 0))
#         # 使用索引來定位具體的產品資料。這些數據被轉換為浮點數，以便於後續的計算。如果沒有找到對應的值，則默認為0。
#         fat_Breakfast = float(request.form.get(f"fat_{index_Breakfast}", 0))
#         protein_Breakfast = float(request.form.get(f"protein_{index_Breakfast}", 0))
#
#         carbohydrates_Lunch = float(request.form.get(f"carbohydrates_{index_Lunch}", 0))
#         # 使用索引來定位具體的產品資料。這些數據被轉換為浮點數，以便於後續的計算。如果沒有找到對應的值，則默認為0。
#         fat_Lunch = float(request.form.get(f"fat_{index_Lunch}", 0))
#         protein_Lunch = float(request.form.get(f"protein_{index_Lunch}", 0))
#
#         carbohydrates_Dinner = float(request.form.get(f"carbohydrates_{index_Dinner}", 0))
#         # 使用索引來定位具體的產品資料。這些數據被轉換為浮點數，以便於後續的計算。如果沒有找到對應的值，則默認為0。
#         fat_Dinner = float(request.form.get(f"fat_{index_Dinner}", 0))
#         protein_Dinner = float(request.form.get(f"protein_{index_Dinner}", 0))
#
#         # 累加值到 session
#
#         session['total_carbs'] = session.get('total_carbs',
#                                              0) + carbohydrates_Breakfast + carbohydrates_Lunch + carbohydrates_Dinner
#         # session.get('total_carbs', 0) 是一個用於從 session 中取出名為 total_carbs的值的方法。
#         # 如果 session 中存在  total_carbs 這個鍵，則會返回其對應的值。如果不存在，則默認返回0。
#         # 當從表單獲取到的新 carbohydrates 值讀取後，程式將這個新值加到先前的 total_carbs 上（如果之前沒有設定，則從0開始加）。
#         session['total_fat'] = session.get('total_fat', 0) + fat_Breakfast + fat_Lunch + fat_Dinner
#         session['total_protein'] = session.get('total_protein', 0) + protein_Breakfast + protein_Lunch + protein_Dinner
#
#         # 儲存當前產品名稱，或者可以改為儲存所有產品的列表
#         if product_name_Breakfast:
#             session['last_product'] = product_name_Breakfast
#         elif product_name_Lunch:
#             session['last_product'] = product_name_Lunch
#         else:
#             session['last_product'] = product_name_Dinner
#
#     return render_template('Diet Journal.html', product_name_Breakfast=product_name_Breakfast,
#                            carbohydrates_Breakfast=carbohydrates_Breakfast, fat_Breakfast=fat_Breakfast,
#                            protein_Breakfast=protein_Breakfast,
#                            product_name_Lunch=product_name_Lunch,
#                            carbohydrates_Lunch=carbohydrates_Lunch,
#                            fat_Lunch=fat_Lunch,
#                            protein_Lunch=protein_Lunch,
#                            product_name_Dinner=product_name_Dinner,
#                            carbohydrates_Dinner=carbohydrates_Dinner,
#                            fat_Dinner=fat_Dinner,
#                            protein_Dinner=protein_Dinner,
#                            total_carbs=session.get('total_carbs', 0),
#                            total_fat=session.get('total_fat', 0),
#                            total_protein=session.get('total_protein', 0))


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

        # 累加值到 session
        session['total_carbs'] = session.get('total_carbs',
                                             0) + carbohydrates_Breakfast + carbohydrates_Lunch + carbohydrates_Dinner
        session['total_fat'] = session.get('total_fat', 0) + fat_Breakfast + fat_Lunch + fat_Dinner
        session['total_protein'] = session.get('total_protein', 0) + protein_Breakfast + protein_Lunch + protein_Dinner

        # 儲存當前產品名稱
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
    # 顯示一個表單讓用戶輸入條形碼
    return render_template('search_Product.html')


@app.route('/search_Product', methods=['GET', 'POST'])
def search_product():
    search_query = request.form.get("product_name")  # 從表單獲取搜索關鍵字
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
    google_maps_api_key = "AIzaSyDAb5nxW_WUizlEfUrhgkiX92J5JnMCQuI"  # Google API金鑰
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


@app.errorhandler(413)
def error_413(error):
    return render_template("errors/413.html"), 413
