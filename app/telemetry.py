"""OpenTelemetry bootstrap — call init_telemetry() once at app startup."""

import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def init_telemetry(service_name: str = "courtvision-api") -> None:
    """Configure the global TracerProvider with appropriate exporters.

    Exporter selection:
    - If OTEL_EXPORTER_OTLP_ENDPOINT is set, use the OTLP HTTP exporter
      (sends to a collector — AWS ADOT, Jaeger, etc.)
    - If OTEL_TRACES_CONSOLE is "true", use ConsoleSpanExporter (local dev)
    - Otherwise, set up the provider with no exporter (tracing is active
      for context propagation but spans are not exported). This is the
      CI/test default — zero overhead, no connection errors.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OpenTelemetry: exporting traces to %s", otlp_endpoint)
    elif os.getenv("OTEL_TRACES_CONSOLE", "").lower() == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry: exporting traces to console")
    else:
        logger.info("OpenTelemetry: tracing enabled (no exporter configured)")

    trace.set_tracer_provider(provider)
