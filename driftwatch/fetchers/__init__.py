"""Auto-import all fetchers so their @register_fetcher decorators run."""
from driftwatch.fetchers import (
    s3,
    ec2,
    rds,
    iam,
    lambda_,
    sns,
    sqs,
    cloudwatch,
    ecs,
    dynamodb,
    elb,
)

__all__ = [
    "s3",
    "ec2",
    "rds",
    "iam",
    "lambda_",
    "sns",
    "sqs",
    "cloudwatch",
    "ecs",
    "dynamodb",
    "elb",
]
