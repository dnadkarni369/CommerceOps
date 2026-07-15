"""
order-notification Lambda

Triggered via SNS whenever:
  - the CloudWatch high-CPU alarm on the app Auto Scaling Group fires, or
  - anything else is published to the commerceops-alerts SNS topic.

Demonstrates the serverless piece of the architecture: infra events (scaling,
alarms) get turned into a notification without needing an always-on server.
In a real deployment this would forward to Slack/email/PagerDuty; here it
logs a structured message to CloudWatch Logs so it's easy to verify in the
AWS console or via `aws logs tail`.
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        message = sns.get("Message", "")
        subject = sns.get("Subject", "commerceops alert")

        logger.info(f"[ALERT] subject={subject} message={message}")

        # Placeholder for real notification delivery (Slack webhook, email
        # via SES, PagerDuty, etc.) - kept out of scope here to avoid
        # requiring extra secrets/credentials for a demo project.

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(event.get("Records", []))}),
    }
