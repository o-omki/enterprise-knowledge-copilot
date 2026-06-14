import os

# Set fallback environment variables for tests
os.environ["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "test_secret_key_change_in_production")
os.environ["JWT_ALGORITHM"] = os.getenv("JWT_ALGORITHM", "HS256")
