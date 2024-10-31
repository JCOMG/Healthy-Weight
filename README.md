# Intelligent methodology for managing healthy weight
This project, Intelligent Health Weight System, aims to assist users in managing and tracking healthy weight goals using a Flask-based application. The system includes a backend that processes and records user data, providing insightful feedback and recommendations.


## Main Features
- Future Weight Predictions : Calculate BMR, RMR, and TDEE calculations to offer health insights and predict future weight.
- Local Gym System : Using Google Maps to help users locate nearby gyms and navigate based on their location.
- Food Recommendations : Provides basic, goal-oriented food recipe recommendations to support users' fitness objectives.
- AI Chatbot : Integrates an AI chatbot based on Llama 3 technology, providing real-time health advice and emotional support to improve user engagement and satisfaction.

## Project Structure
- app / views.py : Main application folder containing Flask routes, views, and other core files for back-end development.
- app / static : This directory contains all the static assets, such as CSS, JavaScript, and image files
- app / templates : This folder is dedicated to HTML files that serve as the application's front-end templates with Jinaj2.
- app / models : Contains database models that define the structure of the application's data.
- app / llama3.py : integrates a Groq API-powered chatbot, using the Llama 3 model, into the application with additional custom fine-tuning to improve response.

## Getting Started
### Prerequisites
- Python 3.12
- Flask
- Jinja2
## Installation
Clone the repo
```bash

git clone git@github.com:JCOMG/Healthy-Weight.git

```
## Running the Application
1. Type this command in the terminal
```bash

flask run 

```

2. Access the application by navigating to http://127.0.0.1:5000 in your browser.

## Tech 
- Python
- Flask
- RESTful API
- Jinja2
- Github
- Git
- SQLite
- SQL
