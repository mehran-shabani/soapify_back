from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class TestRun(Base):
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    test_type = Column(String, index=True)  # voice_upload, stt, checklist
    endpoint = Column(String)
    method = Column(String)  # GET, POST, etc.
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    response_time_ms = Column(Float)
    
    # Response
    status_code = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)
    
    # Request/Response details
    request_headers = Column(JSON)
    request_body = Column(JSON)
    response_headers = Column(JSON)
    response_body = Column(JSON)
    
    # Metrics
    request_size_bytes = Column(Integer)
    response_size_bytes = Column(Integer)
    
    # Additional test-specific data
    test_data = Column(JSON)  # For storing test-specific metrics

class VoiceTestResult(Base):
    __tablename__ = "voice_test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, index=True)
    
    # Audio file info
    file_format = Column(String)  # wav, mp3, m4a
    file_size_bytes = Column(Integer)
    duration_seconds = Column(Float)
    sample_rate = Column(Integer)
    bit_rate = Column(Integer)
    channels = Column(Integer)
    
    # Upload metrics
    upload_time_ms = Column(Float)
    upload_speed_mbps = Column(Float)
    
    # Processing metrics
    processing_time_ms = Column(Float)
    transcription_text = Column(Text)
    confidence_score = Column(Float)

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # System metrics
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    disk_usage_percent = Column(Float)
    
    # API metrics
    total_requests = Column(Integer)
    failed_requests = Column(Integer)
    avg_response_time_ms = Column(Float)
    p95_response_time_ms = Column(Float)
    p99_response_time_ms = Column(Float)
    
    # Network metrics
    network_latency_ms = Column(Float)
    packet_loss_percent = Column(Float)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    alert_type = Column(String)  # high_response_time, high_error_rate, etc.
    severity = Column(String)  # info, warning, error, critical
    message = Column(Text)
    details = Column(JSON)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)