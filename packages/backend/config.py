"""Configuration management for Canteen Python implementation."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class with environment variable support."""
    
    def __init__(self):
        """Initialize configuration."""
        self.blockchain_provider = os.getenv('BLOCKCHAIN_PROVIDER', 'http://localhost:7545')
        self.contract_address = os.getenv('CONTRACT_ADDRESS', '0xad42fdE4D1886169370C89ebe74791Df7Ee326F9')
        self.private_key = os.getenv('PRIVATE_KEY', '')
        
        # FHE configuration
        self.memory_mb = int(os.getenv('MEMORY_MB', '4096'))  # Default 4GB
        
        # Network configuration
        self.p2p_port = int(os.getenv('P2P_PORT', '5000'))
        self.web_api_port = int(os.getenv('WEB_API_PORT', '3000'))
        
        # mDNS configuration
        self.mdns_service_name = os.getenv('MDNS_SERVICE_NAME', 'canteen-cluster')
        
        # Docker configuration
        self.docker_socket = os.getenv('DOCKER_SOCKET', '/var/run/docker.sock')
        
        # Scheduler configuration
        self.scheduler_poll_interval = int(os.getenv('SCHEDULER_POLL_INTERVAL', '1000')) / 1000.0  # Convert to seconds
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'info').upper()
    
    def print_config(self):
        """Print current configuration."""
        print('=' * 40)
        print('Canteen Python Configuration')
        print('=' * 40)
        print(f'Blockchain Provider: {self.blockchain_provider}')
        print(f'Contract Address: {self.contract_address}')
        print(f'Private Key: {"***HIDDEN***" if self.private_key else "Auto (Ganache)"}')
        print(f'Available Memory: {self.memory_mb / 1024:.1f} GB ({self.memory_mb} MB)')
        print(f'P2P Port: {self.p2p_port}')
        print(f'Web API Port: {self.web_api_port}')
        print(f'mDNS Service Name: {self.mdns_service_name}')
        print(f'Docker Socket: {self.docker_socket}')
        print(f'Poll Interval: {self.scheduler_poll_interval}s')
        print(f'Log Level: {self.log_level}')
        print('=' * 40)
        print()
