"""Configuration settings for VistA Graph Database."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Neo4j Connection Settings
    neo4j_uri: str = "bolt://localhost:7688"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    neo4j_connection_timeout: float = 30.0
    neo4j_max_connection_lifetime: float = 3600.0
    neo4j_max_connection_pool_size: int = 50

    # File Paths
    vista_source_dir: Path = Path("Vista-M-source-code")
    dd_file_path: Path = Path("Vista-M-source-code/Packages/VA FileMan/Globals/DD.zwr")
    packages_csv_path: Path = Path("Vista-M-source-code/Packages.csv")

    # Processing Configuration
    batch_size: int = 1000
    max_workers: int = 4
    log_level: str = "INFO"

    # Performance Settings
    chunk_size: int = 10000
    enable_progress_bar: bool = True
    enable_validation: bool = True

    # Output Settings
    output_dir: Path = Path("output")
    export_format: str = "json"

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def get_absolute_path(self, path: Path) -> Path:
        """Convert relative path to absolute path relative to project root."""
        if path.is_absolute():
            return path
        return self.project_root / path

    def validate_paths(self) -> bool:
        """Validate that required files exist."""
        dd_path = self.get_absolute_path(self.dd_file_path)
        packages_path = self.get_absolute_path(self.packages_csv_path)

        errors = []
        if not dd_path.exists():
            errors.append(f"DD file not found: {dd_path}")
        if not packages_path.exists():
            errors.append(f"Packages CSV not found: {packages_path}")

        if errors:
            for error in errors:
                print(f"❌ {error}")
            return False
        return True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_neo4j_config() -> dict:
    """Get Neo4j driver configuration."""
    settings = get_settings()
    return {
        "uri": settings.neo4j_uri,
        "auth": (settings.neo4j_user, settings.neo4j_password),
        "database": settings.neo4j_database,
        "connection_timeout": settings.neo4j_connection_timeout,
        "max_connection_lifetime": settings.neo4j_max_connection_lifetime,
        "max_connection_pool_size": settings.neo4j_max_connection_pool_size,
    }
