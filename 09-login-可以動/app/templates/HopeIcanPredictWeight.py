import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# 假設我們有一個數據集，其中包含用戶的卡路里攝入、卡路里消耗和體重變化
data = pd.DataFrame({
    'calories_in': [2000, 2200, 1800, 2100, 2500],
    'calories_out': [1800, 2000, 1700, 1900, 2300],
    'weight_change': [0.1, 0.2, -0.1, 0.0, 0.3]
})

# 特徵和標籤
X = data[['calories_in', 'calories_out']]
y = data['weight_change']

# 分割數據集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 訓練線性迴歸模型
model = LinearRegression()
model.fit(X_train, y_train)

# 預測
y_pred = model.predict(X_test)

# 評估模型
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)

print(f"RMSE: {rmse}")

# 預測新數據
new_data = np.array([[2300, 2100]])
predicted_weight_change = model.predict(new_data)
print(f"Predicted weight change: {predicted_weight_change[0]}")
