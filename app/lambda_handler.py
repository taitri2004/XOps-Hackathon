"""Lambda entrypoint — wraps the FastAPI app with Mangum.

Deployed as the handler `lambda_handler.handler` per compute.tf.
"""
from mangum import Mangum

from src.app import app

handler = Mangum(app, lifespan="off")
