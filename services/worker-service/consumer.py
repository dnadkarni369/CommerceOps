import os
import json
import time
import logging
import threading
import pika
import redis
from prometheus_client import Counter

logger = logging.getLogger("worker-consumer")

ORDERS_PROCESSED = Counter("worker_orders_processed_total", "Total orders processed by worker")
ORDERS_FAILED = Counter("worker_orders_failed_total", "Total orders that failed processing")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)


def process_order(order: dict):
    """Simulate order processing (e.g. inventory check, payment capture)."""
    logger.info(f"processing order {order.get('order_id')}")
    time.sleep(1)  # simulate work
    redis_client.hset(f"order_status:{order['order_id']}", mapping={
        "status": "PROCESSED",
        "item": order.get("item", ""),
        "user_email": order.get("user_email", ""),
    })
    ORDERS_PROCESSED.inc()
    logger.info(f"order {order.get('order_id')} processed")


def callback(ch, method, properties, body):
    try:
        order = json.loads(body)
        process_order(order)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"failed to process message: {e}")
        ORDERS_FAILED.inc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume_forever():
    queue_name = os.getenv("RABBITMQ_QUEUE", "order_queue")
    params = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", 5672)),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "commerceops"),
            os.getenv("RABBITMQ_PASSWORD", "commerceops"),
        ),
        heartbeat=30,
    )

    while True:
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            logger.info(f"worker listening on queue '{queue_name}'")
            channel.start_consuming()
        except Exception as e:
            logger.error(f"connection lost, retrying in 5s: {e}")
            time.sleep(5)


def start_background_consumer():
    thread = threading.Thread(target=consume_forever, daemon=True)
    thread.start()
