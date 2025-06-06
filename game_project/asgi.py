import os
from dotenv import load_dotenv
from django.core.asgi import get_asgi_application

# Load .env so that environment variables (e.g. GROQ_API_TOKEN) are available
load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "game_project.settings")

application = get_asgi_application()
