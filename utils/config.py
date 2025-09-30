# Configuration for Multimodal RAG System Performance Settings

class RAGConfig:
    """Configuration class for RAG processing performance settings"""
    
    # Embedding Settings
    EMBEDDING_MAX_WORKERS = None  # None = auto-detect optimal number
    EMBEDDING_BATCH_SIZE = 20     # Number of texts to embed in each batch
    
    # Document Processing Settings
    DOC_PROCESSING_MAX_WORKERS = None  # None = auto-detect optimal number
    CHUNK_SIZE = 300              # Size of text chunks for splitting
    CHUNK_OVERLAP = 100           # Overlap between consecutive chunks
    
    # Image Processing Settings
    IMAGE_MAX_WORKERS = 4         # Max concurrent image processing tasks
    
    # File Processing Settings
    FILE_BATCH_SIZE = 10          # Number of files to process in parallel
    
    # Connection Settings
    USE_SESSION_POOLING = True    # Use connection pooling for API requests
    REQUEST_TIMEOUT = 30          # Timeout for API requests in seconds
    MAX_RETRIES = 3               # Maximum number of retries for failed requests
    
    # Memory Management
    ENABLE_PROGRESS_LOGGING = True  # Show detailed progress information
    
    @classmethod
    def get_optimal_workers(cls, task_type: str = "cpu") -> int:
        """Get optimal number of workers based on system capabilities"""
        import os
        cpu_count = os.cpu_count() or 4
        
        if task_type == "cpu":
            # For CPU-bound tasks
            return min(32, cpu_count + 4)
        elif task_type == "io":
            # For I/O-bound tasks (like API calls)
            return min(32, cpu_count * 2)
        elif task_type == "mixed":
            # For mixed workloads
            return min(16, cpu_count + 2)
        else:
            return cpu_count
    
    @classmethod
    def update_from_dict(cls, config_dict: dict):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            if hasattr(cls, key.upper()):
                setattr(cls, key.upper(), value)
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Get current configuration as dictionary"""
        return {
            attr.lower(): getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        }


# Performance presets for different system capabilities
class PerformancePresets:
    """Predefined performance presets for different system configurations"""
    
    LOW_END = {
        "embedding_max_workers": 2,
        "embedding_batch_size": 5,
        "doc_processing_max_workers": 2,
        "image_max_workers": 1,
        "file_batch_size": 3,
        "chunk_size": 200,
        "chunk_overlap": 50
    }
    
    MEDIUM = {
        "embedding_max_workers": 4,
        "embedding_batch_size": 10,
        "doc_processing_max_workers": 4,
        "image_max_workers": 2,
        "file_batch_size": 6,
        "chunk_size": 300,
        "chunk_overlap": 100
    }
    
    HIGH_END = {
        "embedding_max_workers": 8,
        "embedding_batch_size": 30,
        "doc_processing_max_workers": 8,
        "image_max_workers": 4,
        "file_batch_size": 15,
        "chunk_size": 400,
        "chunk_overlap": 120
    }
    
    @classmethod
    def apply_preset(cls, preset_name: str):
        """Apply a performance preset to the configuration"""
        preset_map = {
            "low": cls.LOW_END,
            "medium": cls.MEDIUM,
            "high": cls.HIGH_END
        }
        
        if preset_name.lower() in preset_map:
            RAGConfig.update_from_dict(preset_map[preset_name.lower()])
        else:
            raise ValueError(f"Unknown preset: {preset_name}. Available: low, medium, high")


# Utility functions for configuration management
def optimize_for_system():
    """Auto-optimize configuration based on system capabilities"""
    import os
    cpu_count = os.cpu_count() or 4
    
    if cpu_count >= 8:
        PerformancePresets.apply_preset("high")
    elif cpu_count >= 4:
        PerformancePresets.apply_preset("medium")
    else:
        PerformancePresets.apply_preset("low")

def get_performance_info() -> dict:
    """Get information about current performance configuration"""
    import os
    return {
        "system_cpu_count": os.cpu_count(),
        "current_config": RAGConfig.get_config_dict(),
        "recommended_preset": "high" if os.cpu_count() >= 8 else "medium" if os.cpu_count() >= 4 else "low"
    }