"""Scheduler for polling smart contract and managing Docker containers."""
import logging
import json
import socket
from typing import Optional
from web3 import Web3
import docker
import trio
from fhe_helper import FHEHelper

logger = logging.getLogger(__name__)


class CanteenScheduler:
    """Manages container scheduling based on smart contract state."""
    
    def __init__(self, cluster, contract_address: str, provider_url: str, private_key: str, 
                 memory_mb: int = 4096, node_port: int = 5000):
        """Initialize scheduler.
        
        Args:
            cluster: CanteenCluster instance
            contract_address: Ethereum contract address
            provider_url: Blockchain provider URL
            private_key: Private key for transactions (empty to use Ganache account)
            memory_mb: Available memory in MB for FHE encryption
            node_port: P2P port of this node (used for container port calculation)
        """
        self.cluster = cluster
        self.contract_address = contract_address
        self.provider_url = provider_url
        self.private_key = private_key
        self.memory_mb = memory_mb
        self.node_port = node_port
        
        # Will be initialized in start()
        self.w3 = None
        self.contract = None
        self.account = None
        self.docker_client = None
        self.fhe_helper = None  # FHE helper for encryption
        
        # Container state - track by unique key (image_name:index)
        self.current_containers = {}  # Dict[container_key, container_object]
        self.current_image = None  # Kept for backward compatibility
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False
    
    def _find_available_port(self, start_port: int = 8080, max_attempts: int = 100) -> int:
        """Find an available port starting from start_port.
        
        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try
            
        Returns:
            Available port number
            
        Raises:
            RuntimeError: If no available port found
        """
        for offset in range(max_attempts):
            port = start_port + offset
            if self._is_port_available(port):
                return port
        
        raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")
    
    def _get_account_address(self):
        """Get account address (handles both Account object and string address)."""
        if isinstance(self.account, str):
            return self.account
        return self.account.address
    
    async def _send_transaction(self, tx_function):
        """Send a transaction, handling both localhost and remote providers.
        
        Args:
            tx_function: Contract function ready to be called
            
        Returns:
            (tx_hash, receipt) tuple
        """
        if isinstance(self.account, str):
            # Localhost with Ganache - use .transact()
            tx_hash = tx_function.transact({
                'from': self.account,
                'gas': 6000000
            })
        else:
            # Remote provider (Sepolia/Infura) - sign locally
            tx = tx_function.build_transaction({
                'from': self.account.address,
                'gas': 6000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash, receipt
    
    async def initialize(self):
        """Initialize the scheduler components."""
        logger.info("Initializing scheduler...")
        
        # Initialize FHE helper
        logger.info("Initializing FHE helper (this may take a moment)...")
        self.fhe_helper = FHEHelper()
        logger.info("✓ FHE helper initialized")
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
        
        if not self.w3.is_connected():
            raise Exception(f"Failed to connect to blockchain at {self.provider_url}")
        
        logger.info(f"✓ Connected to blockchain")
        
        # Get account
        if self.private_key:
            # For Sepolia/Infura: Store account object for signing
            self.account = self.w3.eth.account.from_key(self.private_key)
            logger.info(f"Using private key account: {self.account.address}")
        else:
            # For localhost: Use first Ganache account (address string)
            accounts = self.w3.eth.accounts
            if not accounts:
                raise Exception("No accounts available in Ganache")
            self.account = accounts[0]
            logger.info(f"Using Ganache account: {self.account}")
        
        # Load contract - Try Hardhat artifacts with relative path
        from pathlib import Path
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent.parent
        
        contract_paths = [
            project_root / 'packages/hardhat/artifacts/contracts/Canteen.sol/Canteen.json',
            project_root / 'packages/hardhat/artifacts/contracts/CanteenFHEVM.sol/CanteenFHEVM.json',
        ]
        
        contract_loaded = False
        for contract_path in contract_paths:
            try:
                with open(contract_path) as f:
                    contract_json = json.load(f)
                    self.contract = self.w3.eth.contract(
                        address=self.contract_address,
                        abi=contract_json['abi']
                    )
                logger.info(f"✓ Loaded contract from {contract_path}")
                contract_loaded = True
                break
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error(f"Failed to load contract from {contract_path}: {e}")
                continue
        
        if not contract_loaded:
            raise Exception(f"Could not load contract ABI from any of: {contract_paths}")
            raise
        
        # Initialize Docker client
        try:
            self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            self.docker_client.ping()
            logger.info("✓ Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
        
        # Clean up any exited/crashed containers from previous runs
        await self._cleanup_exited_containers()
        
        # Register node with contract
        await self.register_node()
        
        logger.info("✓ Scheduler initialized")
    
    async def _cleanup_exited_containers(self):
        """Clean up any exited or crashed containers to free up ports."""
        try:
            exited_containers = await trio.to_thread.run_sync(
                lambda: self.docker_client.containers.list(
                    all=True,
                    filters={'status': 'exited'}
                )
            )
            
            if exited_containers:
                logger.info(f"Found {len(exited_containers)} exited containers, cleaning up...")
                for container in exited_containers:
                    try:
                        await trio.to_thread.run_sync(lambda c=container: c.remove())
                        logger.info(f"  ✓ Removed exited container: {container.id[:12]}")
                    except Exception as e:
                        logger.warning(f"  Failed to remove container {container.id[:12]}: {e}")
                logger.info("✓ Exited containers cleaned up")
            else:
                logger.info("✓ No exited containers to clean up")
                
        except Exception as e:
            logger.warning(f"Error cleaning up exited containers: {e}")
    
    async def register_node(self):
        """Register this node with the smart contract with encrypted memory."""
        host_id = self.cluster.get_host()
        logger.info(f"Registering node with contract: {host_id}")
        logger.info(f"Available memory: {self.memory_mb / 1024:.1f} GB ({self.memory_mb} MB)")
        
        try:
            # Old Canteen.sol uses addMember(host, encryptedMemory) with bytes
            # Encrypt memory using FHE
            logger.info("Encrypting memory with FHE...")
            encrypted_memory = self.fhe_helper.encrypt_memory(self.memory_mb)
            encrypted_hex = self.fhe_helper.format_for_contract(encrypted_memory)
            logger.info(f"✓ Memory encrypted (ciphertext size: {len(encrypted_hex)} bytes)")
            
            # Send transaction (works with both localhost and Sepolia)
            tx_hash, receipt = await self._send_transaction(
                self.contract.functions.addMember(host_id, encrypted_hex)
            )
            logger.info(f"📝 Transaction sent: {tx_hash.hex()[:10]}...")
            
            if receipt.status == 1:
                logger.info(f"✓ Node registered with encrypted memory (tx: {tx_hash.hex()[:10]}...)")
            else:
                logger.error(f"Transaction failed: {receipt}")
        except Exception as e:
            error_msg = str(e)
            if "revert" in error_msg.lower():
                logger.info("Node already registered. Continuing...")
            else:
                logger.error(f"Failed to register node: {e}")
                raise
    
    def get_contract_members(self):
        """Get list of all registered members from the smart contract.
        
        Returns:
            List of member peer IDs (host identifiers)
        """
        try:
            members = []
            index = 0
            
            # Iterate through members array in contract
            while True:
                try:
                    member_host = self.contract.functions.members(index).call()
                    if not member_host:
                        break
                    
                    # Check if member is active
                    details = self.contract.functions.getMemberDetails(member_host).call()
                    is_active = details[1]  # active boolean from Member struct
                    
                    if is_active:
                        members.append(member_host)
                    
                    index += 1
                except Exception:
                    # End of array or error accessing index
                    break
            
            return members
        except Exception as e:
            logger.error(f"Error getting contract members: {e}")
            return []
    
    async def poll_loop(self, interval: float):
        """Poll contract for image assignments and manage multiple containers.
        
        Args:
            interval: Polling interval in seconds
        """
        host_id = self.cluster.get_host()
        
        while True:
            try:
                # Query contract for all assigned images (supports multiple containers)
                assigned_images = self.contract.functions.getMemberImages(host_id).call()
                
                # Build list of container keys with indices (e.g., "nginx:latest:0", "nginx:latest:1")
                assigned_keys = []
                for idx, image in enumerate(assigned_images):
                    container_key = f"{image}:{idx}"
                    assigned_keys.append(container_key)
                
                # Convert to sets for comparison
                assigned_set = set(assigned_keys)
                current_set = set(self.current_containers.keys())
                
                # Find containers to add and remove
                to_add = assigned_set - current_set
                to_remove = current_set - assigned_set
                
                # Remove containers that are no longer assigned
                for container_key in to_remove:
                    logger.info(f"Removing container: {container_key}")
                    await self.remove_container(container_key)
                
                # Add new containers
                for container_key in to_add:
                    # Extract image name from key (e.g., "nginx:latest:0" -> "nginx:latest")
                    image_name = ":".join(container_key.split(":")[:-1])
                    logger.info(f"Adding new container: {image_name} (key: {container_key})")
                    await self.deploy_container(container_key, image_name)
                
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
            
            await trio.sleep(interval)
    
    async def deploy_container(self, container_key: str, image_name: str):
        """Pull and run a Docker container (supports multiple containers).
        
        Args:
            container_key: Unique container identifier (e.g., "nginx:latest:0")
            image_name: Docker image name (e.g., 'nginx:latest')
        """
        logger.info(f"Deploying container: {image_name} ({container_key})")
        
        try:
            # Run Docker operations in thread pool (they're blocking)
            # Pull image
            logger.info(f"Pulling image: {image_name}...")
            await trio.to_thread.run_sync(
                lambda: self.docker_client.images.pull(image_name)
            )
            logger.info(f"✓ Image pulled: {image_name}")
            
            # Determine container's internal port and find available host port
            # Common container ports: nginx uses 80, hello-world doesn't expose ports
            container_port = 80  # Default for nginx
            if "hello-world" in image_name:
                # hello-world doesn't need port mapping
                container_port = None
            
            # Find an available host port dynamically
            if container_port:
                # Start search from base port + node offset for better distribution
                node_offset = self.node_port - 5000
                start_port = 8080 + node_offset
                port = await trio.to_thread.run_sync(
                    lambda: self._find_available_port(start_port)
                )
                logger.info(f"Found available port: {port}")
                
                # Create and start new container with port mapping
                logger.info(f"Starting container {image_name} on port {port}...")
                container = await trio.to_thread.run_sync(
                    lambda: self.docker_client.containers.run(
                        image_name,
                        detach=True,
                        ports={f'{container_port}/tcp': port},
                        remove=False
                    )
                )
            else:
                # No port mapping needed
                logger.info(f"Starting container {image_name} (no port mapping)...")
                container = await trio.to_thread.run_sync(
                    lambda: self.docker_client.containers.run(
                        image_name,
                        detach=True,
                        remove=False
                    )
                )
                port = None
            
            # Store container in our dictionary using unique key (supports multiple containers)
            self.current_containers[container_key] = container
            self.current_image = image_name  # Update for backward compatibility
            
            logger.info(f"✓ Container started: {container.id[:12]}")
            logger.info(f"  Container Key: {container_key}")
            logger.info(f"  Image: {image_name}")
            if port:
                logger.info(f"  Host Port: {port} -> Container Port: {container_port}")
            
            # Update memory: reduce by 200 MB (0.2 GB) and update in contract
            await self.reduce_and_update_memory(200)
            
        except Exception as e:
            logger.error(f"Failed to deploy container: {e}")
            raise
    
    async def remove_container(self, container_key: str):
        """Remove a specific container by container key.
        
        Args:
            container_key: Unique container identifier (e.g., "nginx:latest:0")
        """
        if container_key not in self.current_containers:
            logger.warning(f"Container {container_key} not found in current containers")
            return
        
        try:
            container = self.current_containers[container_key]
            logger.info(f"Stopping container {container_key} ({container.id[:12]})...")
            
            await trio.to_thread.run_sync(
                lambda: self._stop_single_container(container)
            )
            
            del self.current_containers[container_key]
            logger.info(f"✓ Container {container_key} removed")
            
        except Exception as e:
            logger.error(f"Error removing container {container_key}: {e}")
    
    def _stop_single_container(self, container):
        """Stop a single container (blocking operation).
        
        Args:
            container: Docker container object
        """
        try:
            container.stop(timeout=10)
            container.remove()
            logger.info(f"✓ Container stopped and removed: {container.id[:12]}")
        except Exception as e:
            logger.warning(f"Error stopping container {container.id[:12]}: {e}")
    
    def _stop_container(self):
        """Stop current container (blocking operation)."""
        if self.current_container:
            try:
                self.current_container.stop(timeout=10)
                self.current_container.remove()
                logger.info(f"✓ Old container stopped and removed")
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")
    
    async def cleanup_container(self):
        """Clean up all containers."""
        logger.info("Cleaning up all containers...")
        
        if self.current_containers:
            for container_key in list(self.current_containers.keys()):
                await self.remove_container(container_key)
            
            logger.info("✓ All containers cleaned up")
        else:
            logger.info("No containers to clean up")
    
    async def reduce_and_update_memory(self, amount_mb: int):
        """Reduce available memory after container deployment and update contract.
        
        Args:
            amount_mb: Amount of memory to reduce (e.g., 200 MB for 0.2 GB)
        """
        host_id = self.cluster.get_host()
        logger.info(f"Updating memory after deployment (reducing by {amount_mb} MB)...")
        
        try:
            # Reduce current memory
            self.memory_mb -= amount_mb
            if self.memory_mb < 0:
                self.memory_mb = 0
            
            logger.info(f"New available memory: {self.memory_mb / 1024:.1f} GB ({self.memory_mb} MB)")
            
            # Encrypt new memory value
            encrypted_memory = self.fhe_helper.encrypt_memory(self.memory_mb)
            encrypted_hex = self.fhe_helper.format_for_contract(encrypted_memory)
            
            # Send transaction (works with both localhost and Sepolia)
            tx_hash, receipt = await self._send_transaction(
                self.contract.functions.updateMemberMemory(host_id, encrypted_hex)
            )
            
            if receipt.status == 1:
                logger.info(f"✓ Memory updated in contract (tx: {tx_hash.hex()[:10]}...)")
            else:
                logger.error(f"Failed to update memory: {receipt}")
        
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            # Don't raise - container is already running
    
    async def unregister_node(self):
        """Unregister this node from the smart contract."""
        host_id = self.cluster.get_host()
        logger.info(f"Unregistering node from contract: {host_id}")
        
        try:
            # Define blocking function to check if registered and unregister
            def _unregister():
                # First check if we're actually registered
                member_details = self.contract.functions.getMemberDetails(host_id).call()
                image_name = member_details[0]  # First element is 'imageName' string
                is_active = member_details[1]  # Second element is 'active' boolean
                
                logger.info(f"Contract state - imageName: '{image_name}', active: {is_active}")
                
                if not is_active:
                    logger.info("Node not registered in contract, skipping unregistration")
                    return None, None
                
                # Proceed with unregistration (contract now handles empty images properly)
                if image_name:
                    logger.info(f"Node has image '{image_name}', unregistering...")
                else:
                    logger.info("Node has no image assigned, unregistering...")
                
                # Note: We can't use await in a sync function passed to trio.to_thread.run_sync
                # So we'll build and send the transaction directly here
                if isinstance(self.account, str):
                    # Localhost with Ganache
                    tx_hash = self.contract.functions.removeMember(host_id).transact({
                        'from': self.account,
                        'gas': 6000000
                    })
                else:
                    # Remote provider - sign locally
                    tx = self.contract.functions.removeMember(host_id).build_transaction({
                        'from': self.account.address,
                        'gas': 6000000,
                        'gasPrice': self.w3.eth.gas_price,
                        'nonce': self.w3.eth.get_transaction_count(self.account.address)
                    })
                    signed_tx = self.account.sign_transaction(tx)
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                return tx_hash, receipt
            
            # Run in thread
            result = await trio.to_thread.run_sync(_unregister)
            
            if result[0] is None:
                # Not registered or no image, already logged
                return
            
            tx_hash, receipt = result
            
            if receipt['status'] == 1:
                logger.info(f"✓ Node unregistered successfully")
                logger.info(f"  Transaction: {tx_hash.hex()}")
            else:
                logger.warning(f"Node unregistration transaction failed")
                
        except Exception as e:
            logger.error(f"Failed to unregister node: {e}")
    
    async def cleanup(self):
        """Cleanup scheduler resources."""
        logger.info("Cleaning up scheduler...")
        
        # Stop any running containers
        await self.cleanup_container()
        
        # Unregister from contract
        await self.unregister_node()
