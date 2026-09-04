from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

models = client.models.list()

for model in models.data:
    print(model.id)