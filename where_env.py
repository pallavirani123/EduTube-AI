from decouple import Config, RepositoryEnv
import os

cwd = os.getcwd()
print("Current working directory:", cwd)

for root, dirs, files in os.walk(cwd):
    if ".env" in files:
        print("Found .env in:", root)

try:
    config = Config(RepositoryEnv('.env'))
    print("Loaded from:", os.path.abspath('.env'))
    print("YOUTUBE_API_KEY:", config('YOUTUBE_API_KEY'))
except Exception as e:
    print("Error loading .env:", e)
