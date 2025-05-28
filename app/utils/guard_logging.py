import logging

logging.basicConfig(
    filename='guardrails.log',
    filemode='a',
    level=logging.INFO,
    format='[GUARDRAILS LOG] %(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
