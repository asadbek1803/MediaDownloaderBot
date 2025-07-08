from environs import Env

# environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# .env fayl ichidan quyidagilarni o'qiymiz
BOT_TOKEN = env.str("BOT_TOKEN")  # Bot Token

DB_URL = env.str("DB_URL", "postgres://user:password@localhost:5432/dbname")  # PostgreSQL URL

BACKEND_HOST = env.str("BACKEND_HOST", "http://localhost:8000")
