import os
import json
import time
import logging
import pika

logger = logging.getLogger(__name__)

def publish_order_event(order: dict, retries=5, delay=2):
    """Publish an order-created event to RabbitMQ. Non-fatal on failure -
    order is already persisted in Postgres, the queue is for async processing only."""
    params = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", 5672)),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "commerceops"),
            os.getenv("RABBITMQ_PASSWORD", "commerceops"),
        ),
    )
    queue_name = os.getenv("RABBITMQ_QUEUE", "order_queue")

    for attempt in range(retries):
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(order),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            connection.close()
            return True
        except Exception as e:
            logger.warning(f"rabbitmq publish attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    logger.error("failed to publish order event after retries")
    return False
