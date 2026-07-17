import os



# Mock critical environment variables for test collection so that top-level module imports
# in app.py and LangChain don't crash when .env is missing (e.g. in GitHub Actions CI/CD).
os.environ.setdefault("PORTER_API_KEY", "dummy_test_porter_api_key")
os.environ.setdefault("PORTER_ADMIN_KEY", "default_dev_key")
os.environ.setdefault("JWT_SECRET", "dummy_test_jwt_secret_key")
os.environ.setdefault("GROQ_API_KEY", "dummy_test_groq_api_key")
