"""FastAPI entrypoint for the Vercel simulation deployment."""

from prototype.app import create_app

app = create_app(hosted=True)
