"""
EcoTrack logging and distributed tracing service.

Configures structured stream logging for Cloud Run and optional
OpenTelemetry Cloud Trace integration when running on GCP.
"""
import logging
from opentelemetry import trace

from backend.config import IS_GCP, GOOGLE_CLOUD_PROJECT

__all__ = ["setup_logging", "setup_tracing", "get_tracer"]

# Pre-initialize module-level logger
logger = logging.getLogger("ecotrack")
logger.setLevel(logging.INFO)

# Module-level tracer, populated by setup_tracing()
_tracer: trace.Tracer | None = None


def setup_logging() -> logging.Logger:
    """
    Configure standard StreamHandler logging to stdout.

    Cloud Run automatically collects standard output stream logs.
    Returns the configured 'ecotrack' logger instance.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    configured_logger = logging.getLogger("ecotrack")
    configured_logger.setLevel(logging.INFO)
    configured_logger.info("Stream logging initialized.")
    return configured_logger


def setup_tracing() -> None:
    """
    Configure OpenTelemetry tracing provider.

    On GCP (Cloud Run): uses CloudTraceSpanExporter with BatchSpanProcessor.
    Locally: installs a NoOpTracerProvider so tracing calls are silently ignored.
    """
    global _tracer

    if IS_GCP:
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter

            provider = TracerProvider()
            exporter = CloudTraceSpanExporter(project_id=GOOGLE_CLOUD_PROJECT)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            _tracer = trace.get_tracer("ecotrack")
            logger.info("OpenTelemetry Cloud Trace initialized.")
        except Exception as exc:
            logger.warning(
                f"Failed to setup OpenTelemetry: {exc}. Falling back to NoOpTracerProvider."
            )
            trace.set_tracer_provider(trace.NoOpTracerProvider())
            _tracer = trace.get_tracer("ecotrack")
    else:
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        _tracer = trace.get_tracer("ecotrack")


def get_tracer() -> trace.Tracer:
    """Return the configured OpenTelemetry tracer, initialising lazily if needed."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("ecotrack")
    return _tracer
