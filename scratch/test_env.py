import os
from dotenv import load_dotenv

load_dotenv()
client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

print(f"CLIENT_ID: {client_id}")
print(f"CLIENT_SECRET: {'***' + client_secret[-4:] if client_secret else 'None'}")
