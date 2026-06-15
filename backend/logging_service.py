import logging
import os
from backend.config import IS_GCP, GOOGLE_CLOUD_PROJECT

# Pre-initialize logger
logger = logging.getLogger("ecotrack")
logger.setLevel(logging.INFO)

def setup_logging() -> logging.Logger:
    """
    Setup standard StreamHandler logging to stdout/stderr.
    Cloud Run automatically collects standard output stream logs.
    """
    global logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("ecotrack")
    logger.setLevel(logging.INFO)
    logger.info("Stream logging initialized.")
    return logger

_tracer = None

def setup_tracing() -> None:
    """
    If IS_GCP: OpenTelemetry with CloudTraceSpanExporter.
    Else: NoOpTracerProvider silently.
    """
    global _tracer
    from opentelemetry import trace
    
    if IS_GCP:
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter
            
            provider = TracerProvider()
            exporter = CloudTraceSpanExporter(project_id=GOOGLE_CLOUD_PROJECT)
            span_processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(span_processor)
            trace.set_tracer_provider(provider)
            _tracer = trace.get_tracer("ecotrack")
            logger.info("OpenTelemetry Cloud Trace initialized.")
        except Exception as e:
            logger.warning(f"Failed to setup OpenTelemetry: {str(e)}. Fallback to NoOpTracerProvider.")
            from opentelemetry.trace import NoOpTracerProvider
            trace.set_tracer_provider(NoOpTracerProvider())
            _tracer = trace.get_tracer("ecotrack")
    else:
        from opentelemetry.trace import NoOpTracerProvider
        trace.set_tracer_provider(NoOpTracerProvider())
        _tracer = trace.get_tracer("ecotrack")

def get_tracer():
    """Return the configured OpenTelemetry tracer."""
    global _tracer
    if _tracer is None:
        from opentelemetry import trace
        _tracer = trace.get_tracer("ecotrack")
    return _tracer
