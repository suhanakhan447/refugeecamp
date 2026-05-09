import os

class Config:
    SECRET_KEY = 'your-secret-key-change-this'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///fairness.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    APP_NAME = "FairShare"
    APP_VERSION = "2.0.0"
    
    # Resource thresholds
    FOOD_THRESHOLD_CRITICAL = 500
    WATER_THRESHOLD_CRITICAL = 1000
    MEDICINE_THRESHOLD_CRITICAL = 50