"""
Kafka consumer — listens on `hint.requested`, runs the LangGraph pipeline,
then publishes results to `hint.ready`.
"""
import json
import logging
import threading
import time
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from app.core.config import settings
from app.graph.pipeline import hint_graph
from app.graph.state import HintState, HintRequest
from app.tools.redis_cache import redis_cache

logger = logging.getLogger(__name__)


def _make_consumer() -> Consumer:
    return Consumer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "group.id": settings.KAFKA_GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })


def _make_producer() -> Producer:
    return Producer({
        "bootstrap.servers": settings.KAFKA_BROKERS,
        "acks": "all",
        "retries": 5,
    })


def _publish_hints(producer: Producer, event_id: str, user_id: str, problem_slug: str, hints: list[str], error: str | None = None):
    payload = {
        "event_id": event_id,
        "user_id": user_id,
        "problem_slug": problem_slug,
        "hints": hints,
        "error": error,
    }
    producer.produce(
        settings.TOPIC_HINT_READY,
        key=user_id.encode(),
        value=json.dumps(payload).encode(),
    )
    producer.poll(0)
    logger.info(f"Published {len(hints)} hints to {settings.TOPIC_HINT_READY} for {user_id}:{problem_slug}")


def _process_event(event: dict, producer: Producer):
    """Run the full LangGraph hint pipeline for one incoming event."""
    event_id = event.get("event_id", "unknown")
    user_id = event.get("user_id", "anonymous")
    problem_slug = event.get("problem_slug", "")

    # Rate limit check
    if not redis_cache.rate_limit_check(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        _publish_hints(producer, event_id, user_id, problem_slug, [], error="Rate limit exceeded")
        return

    req: HintRequest = {
        "user_id": user_id,
        "problem_slug": problem_slug,
        "problem_title": event.get("problem_title", problem_slug.replace("-", " ").title()),
        "difficulty": event.get("difficulty", "medium"),
        "tags": event.get("tags", []),
        "hint_level": event.get("hint_level", 3),
        "user_solve_count": redis_cache.get_solve_count(user_id),
        "user_code": event.get("user_code", ""),  # user's current code approach
    }

    initial_state: HintState = {
        "request": req,
        "topic": "",
        "prerequisites": [],
        "related_topics": [],
        "context_docs": [],
        "cache_hit": False,
        "hints": [],
        "error": None,
    }

    logger.info(f"Running hint pipeline for {user_id}:{problem_slug} (level={req['hint_level']})")
    try:
        result = hint_graph.invoke(initial_state)
        hints = result.get("hints", [])
        error = result.get("error")
        _publish_hints(producer, event_id, user_id, problem_slug, hints, error)
    except Exception as e:
        logger.error(f"Pipeline failed for {problem_slug}: {e}")
        _publish_hints(producer, event_id, user_id, problem_slug, [], error=str(e))


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

def _process_review(event: dict, r):
    """Generate a post-solve AI code review and store it in Redis."""
    user_id = event.get("user_id")
    problem_slug = event.get("problem_slug")
    user_code = event.get("user_code", "").strip()

    if not user_code or not user_id or not problem_slug:
        return

    logger.info(f"Generating post-solve review for {user_id}:{problem_slug}")

    system_prompt = """You are a Staff Software Engineer conducting a post-solve code review.
Analyze the user's working solution for a competitive programming problem.
Output a JSON object with EXACTLY these keys:
{
  "time_complexity": "string (e.g., O(N))",
  "space_complexity": "string (e.g., O(1))",
  "suggestions": ["suggestion 1", "suggestion 2"],
  "refactored_code": "The full code rewritten to be perfectly clean and optimal"
}
Do NOT wrap the JSON in markdown formatting (no ```json ... ```)."""

    user_prompt = f"""Problem: {problem_slug}
Language: {event.get("language")}

User Code:
{user_code[:3000]}"""

    try:
        llm = ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.2,
            max_output_tokens=1500,
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        review = json.loads(raw.strip())
        
        # Save to Redis
        r.set(f"review:{user_id}:{problem_slug}", json.dumps(review))
        logger.info(f"Saved review for {user_id}:{problem_slug}")
    except Exception as e:
        logger.error(f"Failed to generate review: {e}")

def run_consumer_loop():
    """Blocking Kafka consumer loop — runs in a dedicated thread."""
    import redis
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    consumer = _make_consumer()
    producer = _make_producer()

    consumer.subscribe([settings.TOPIC_HINT_REQUESTED, settings.TOPIC_SOLVE_COMPLETED])
    logger.info(f"Subscribed to {settings.TOPIC_HINT_REQUESTED} and {settings.TOPIC_SOLVE_COMPLETED}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            try:
                event = json.loads(msg.value().decode("utf-8"))
                if msg.topic() == settings.TOPIC_SOLVE_COMPLETED:
                    _process_review(event, r)
                elif msg.topic() == settings.TOPIC_HINT_REQUESTED:
                    _process_event(event, producer)
            except json.JSONDecodeError as e:
                logger.error(f"Malformed Kafka message: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing message: {e}")
    except KeyboardInterrupt:
        logger.info("Consumer shutting down…")
    finally:
        consumer.close()
        producer.flush()
        r.close()


def start_consumer_thread() -> threading.Thread:
    """Start the Kafka consumer in a background daemon thread."""
    t = threading.Thread(target=run_consumer_loop, daemon=True, name="kafka-hint-consumer")
    t.start()
    logger.info("Kafka consumer thread started")
    return t
