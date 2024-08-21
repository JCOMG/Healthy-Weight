import unittest
from app import app


class BasicTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        self.login()

    def login(self):
        response = self.app.post('/login', data=dict(username='Kimmy', password='11'), follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_home_page_redirect(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_home_page(self):
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Expected content after login', response.data)

    def test_bmr_calculation(self):
        response = self.app.post('/Calculate_BMR', data=dict(
            gender='male',
            weight=70,
            height=175,
            age=25,
            activity_level='1.2',
            BmrRmr='BMR formula : The Harris-Benedict Equation (revised by Roza and Shizgal in 1984)',
            fitness_goal='gain',
            days=30
        ))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'recommended calorie intake', response.data.lower())
        # 打印出response的data以便調試
        print(response.data.decode('utf-8'))

    def test_recommendation_recipe(self):
        response = self.app.post('/DietJournal', data=dict(
            gender='male',
            weight=70,
            height=175,
            age=25,
            activity_level='1.2',
            BmrRmr='BMR formula : The Harris-Benedict Equation (revised by Roza and Shizgal in 1984)',
            fitness_goal='gain',
            days=30
        ))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Recommendation', response.data)
        # 檢查推薦的食譜是否存在
        self.assertIn(b'Title of a recommended recipe', response.data)
        # 打印出response的data以便調試
        print(response.data.decode('utf-8'))


if __name__ == "__main__":
    unittest.main()
