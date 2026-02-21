"""
Configuration loader module.
Handles loading YAML configuration files.
"""
import os
import yaml  # type: ignore
from typing import Dict, Any


def load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML file and return as dictionary.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Dictionary containing parsed YAML content
        
    Raises:
        FileNotFoundError: If file does not exist
        yaml.YAMLError: If YAML parsing fails
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_config_path(filename: str) -> str:
    """Get absolute path to config file based on this module's location.
    
    Args:
        filename: Name of config file (e.g. 'secrets.yaml')
        
    Returns:
        Absolute path to config file
    """
    # This module is in src/ directory
    # Config files are in ../config/ (parent directory's config)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(src_dir)
    path = os.path.join(root_dir, "config", filename)
    # Normalize to forward slashes for test expectations
    return path.replace("\\", "/")


def load_secrets() -> Dict[str, Any]:
    """Load secrets configuration from config/secrets.yaml.
    
    Returns:
        Dictionary with API keys and credentials
    """
    return load_yaml(_get_config_path("secrets.yaml"))


def load_generation_policy() -> Dict[str, Any]:
    """Load generation policy configuration from config/generation_policy.yaml.
    
    Returns:
        Dictionary with generation policies and parameters
    """
    return load_yaml(_get_config_path("generation_policy.yaml"))


def load_accounts() -> Dict[str, Any]:
    """Load accounts configuration from config/accounts.yaml.
    
    Returns:
        Dictionary mapping account names to account configurations
    """
    # Return the raw mapping (dict) so integration callers receive mapping
    return load_yaml(_get_config_path("accounts.yaml"))


def load_themes() -> Dict[str, Any]:
    """Load themes configuration from config/themes.yaml.
    
    Returns:
        Dictionary with theme definitions
    """
    return load_yaml(_get_config_path("themes.yaml"))
