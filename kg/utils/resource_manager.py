# Resource Management System for KG-System
# Handles GPU/CPU allocation, locking, and deadlock prevention

import asyncio
import threading
import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import psutil
import json

class ResourceType(Enum):
    """Types of resources that can be managed"""
    CPU_CORE = "cpu_core"
    GPU_SLOT = "gpu_slot"
    MEMORY_GB = "memory_gb"
    DISK_GB = "disk_gb"
    NETWORK_BANDWIDTH = "network_bandwidth"

class LockPriority(Enum):
    """Priority levels for resource locks"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ResourceLock:
    """Represents a resource lock"""
    lock_id: str
    task_id: str
    module: str
    resources: Dict[ResourceType, int]
    priority: LockPriority
    acquired_at: datetime
    expires_at: datetime
    timeout_seconds: int = 300
    
    def is_expired(self) -> bool:
        """Check if lock has expired"""
        return datetime.now() > self.expires_at
    
    def extend_timeout(self, additional_seconds: int):
        """Extend lock timeout"""
        self.expires_at += timedelta(seconds=additional_seconds)

@dataclass
class ResourcePool:
    """Represents available resources in the system"""
    cpu_cores: int = 8
    gpu_slots: int = 2
    memory_gb: int = 16
    disk_gb: int = 100
    network_bandwidth: int = 1000  # Mbps
    
    def get_available(self, resource_type: ResourceType) -> int:
        """Get available amount of a resource type"""
        if resource_type == ResourceType.CPU_CORE:
            return self.cpu_cores
        elif resource_type == ResourceType.GPU_SLOT:
            return self.gpu_slots
        elif resource_type == ResourceType.MEMORY_GB:
            return self.memory_gb
        elif resource_type == ResourceType.DISK_GB:
            return self.disk_gb
        elif resource_type == ResourceType.NETWORK_BANDWIDTH:
            return self.network_bandwidth
        return 0
    
    def allocate(self, resource_type: ResourceType, amount: int) -> bool:
        """Allocate resources if available"""
        if resource_type == ResourceType.CPU_CORE and self.cpu_cores >= amount:
            self.cpu_cores -= amount
            return True
        elif resource_type == ResourceType.GPU_SLOT and self.gpu_slots >= amount:
            self.gpu_slots -= amount
            return True
        elif resource_type == ResourceType.MEMORY_GB and self.memory_gb >= amount:
            self.memory_gb -= amount
            return True
        elif resource_type == ResourceType.DISK_GB and self.disk_gb >= amount:
            self.disk_gb -= amount
            return True
        elif resource_type == ResourceType.NETWORK_BANDWIDTH and self.network_bandwidth >= amount:
            self.network_bandwidth -= amount
            return True
        return False
    
    def release(self, resource_type: ResourceType, amount: int):
        """Release allocated resources"""
        if resource_type == ResourceType.CPU_CORE:
            self.cpu_cores += amount
        elif resource_type == ResourceType.GPU_SLOT:
            self.gpu_slots += amount
        elif resource_type == ResourceType.MEMORY_GB:
            self.memory_gb += amount
        elif resource_type == ResourceType.DISK_GB:
            self.disk_gb += amount
        elif resource_type == ResourceType.NETWORK_BANDWIDTH:
            self.network_bandwidth += amount

class ResourceManager:
    """
    Manages system resources with deadlock prevention and priority-based allocation
    """
    
    def __init__(self):
        self.pool = ResourcePool()
        self.active_locks: Dict[str, ResourceLock] = {}
        self.lock_queue: List[ResourceLock] = []
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.logger = logging.getLogger(__name__)
        
        # Deadlock detection
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.lock_hierarchy = ["KD_read", "LAR_write", "ISV_simulation", "HG_generation"]
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_locks, daemon=True)
        self.cleanup_thread.start()
        
        # Initialize with system resources
        self._detect_system_resources()
    
    def _detect_system_resources(self):
        """Detect available system resources"""
        try:
            # CPU cores
            self.pool.cpu_cores = psutil.cpu_count(logical=False) or 4
            
            # Memory
            memory_info = psutil.virtual_memory()
            self.pool.memory_gb = int(memory_info.available / (1024**3))
            
            # Disk space
            disk_info = psutil.disk_usage('/')
            self.pool.disk_gb = int(disk_info.free / (1024**3))
            
            # GPU detection (simplified)
            try:
                import torch
                if torch.cuda.is_available():
                    self.pool.gpu_slots = torch.cuda.device_count()
                else:
                    self.pool.gpu_slots = 0
            except ImportError:
                self.pool.gpu_slots = 0
                
            self.logger.info(f"Detected resources: CPU={self.pool.cpu_cores}, "
                           f"Memory={self.pool.memory_gb}GB, "
                           f"Disk={self.pool.disk_gb}GB, "
                           f"GPU={self.pool.gpu_slots}")
            
        except Exception as e:
            self.logger.error(f"Failed to detect system resources: {e}")
    
    async def acquire_lock(self, 
                          task_id: str, 
                          module: str,
                          resources: Dict[ResourceType, int],
                          timeout_seconds: int = 300,
                          priority: LockPriority = LockPriority.NORMAL) -> Optional[str]:
        """
        Acquire a resource lock with deadlock prevention
        
        Args:
            task_id: ID of the task requesting the lock
            module: Module requesting the lock
            resources: Dict of resource types and amounts needed
            timeout_seconds: Lock timeout in seconds
            priority: Priority level for the lock
            
        Returns:
            Lock ID if successful, None if failed
        """
        lock_id = f"LOCK-{module}-{task_id}-{int(time.time())}"
        
        # Check for deadlock potential
        if self._would_cause_deadlock(task_id, module, resources):
            self.logger.warning(f"Lock request {lock_id} would cause deadlock - rejected")
            return None
        
        # Create lock request
        lock_request = ResourceLock(
            lock_id=lock_id,
            task_id=task_id,
            module=module,
            resources=resources,
            priority=priority,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=timeout_seconds),
            timeout_seconds=timeout_seconds
        )
        
        # Try to acquire lock
        acquired = await self._try_acquire_lock(lock_request)
        
        if acquired:
            self.logger.info(f"Lock acquired: {lock_id}")
            return lock_id
        else:
            self.logger.warning(f"Failed to acquire lock: {lock_id}")
            return None
    
    async def _try_acquire_lock(self, lock_request: ResourceLock) -> bool:
        """Try to acquire a lock with priority handling"""
        max_wait_time = lock_request.timeout_seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            with self.condition:
                # Check if resources are available
                if self._can_allocate_resources(lock_request.resources):
                    # Allocate resources
                    for resource_type, amount in lock_request.resources.items():
                        self.pool.allocate(resource_type, amount)
                    
                    # Add to active locks
                    self.active_locks[lock_request.lock_id] = lock_request
                    
                    # Update dependency graph
                    self._update_dependency_graph(lock_request)
                    
                    return True
                
                # Wait for resources to become available
                await asyncio.sleep(0.1)
        
        return False
    
    def _can_allocate_resources(self, resources: Dict[ResourceType, int]) -> bool:
        """Check if all requested resources can be allocated"""
        for resource_type, amount in resources.items():
            available = self.pool.get_available(resource_type)
            if available < amount:
                return False
        return True
    
    def _would_cause_deadlock(self, task_id: str, module: str, resources: Dict[ResourceType, int]) -> bool:
        """Check if acquiring this lock would cause a deadlock"""
        # Simple deadlock detection based on hierarchy
        module_priority = self._get_module_priority(module)
        
        for lock in self.active_locks.values():
            lock_priority = self._get_module_priority(lock.module)
            if lock_priority > module_priority:
                # Check if resources overlap
                for resource_type in resources:
                    if resource_type in lock.resources:
                        return True
        
        return False
    
    def _get_module_priority(self, module: str) -> int:
        """Get priority for module based on hierarchy"""
        try:
            return self.lock_hierarchy.index(module)
        except ValueError:
            return len(self.lock_hierarchy)  # Lowest priority
    
    def _update_dependency_graph(self, lock_request: ResourceLock):
        """Update dependency graph for deadlock detection"""
        task_id = lock_request.task_id
        if task_id not in self.dependency_graph:
            self.dependency_graph[task_id] = set()
        
        # Add dependencies based on resource conflicts
        for existing_lock in self.active_locks.values():
            if existing_lock.task_id != task_id:
                # Check for resource conflicts
                for resource_type in lock_request.resources:
                    if resource_type in existing_lock.resources:
                        self.dependency_graph[task_id].add(existing_lock.task_id)
    
    def release_lock(self, lock_id: str) -> bool:
        """Release a resource lock"""
        with self.condition:
            if lock_id in self.active_locks:
                lock = self.active_locks[lock_id]
                
                # Release resources
                for resource_type, amount in lock.resources.items():
                    self.pool.release(resource_type, amount)
                
                # Remove from active locks
                del self.active_locks[lock_id]
                
                # Clean up dependency graph
                self._cleanup_dependency_graph(lock.task_id)
                
                # Notify waiting threads
                self.condition.notify_all()
                
                self.logger.info(f"Lock released: {lock_id}")
                return True
            
            return False
    
    def _cleanup_dependency_graph(self, task_id: str):
        """Clean up dependency graph for released task"""
        if task_id in self.dependency_graph:
            del self.dependency_graph[task_id]
        
        # Remove references to this task from other nodes
        for deps in self.dependency_graph.values():
            deps.discard(task_id)
    
    def _cleanup_expired_locks(self):
        """Background thread to clean up expired locks"""
        while True:
            try:
                expired_locks = []
                
                with self.condition:
                    for lock_id, lock in self.active_locks.items():
                        if lock.is_expired():
                            expired_locks.append(lock_id)
                
                # Release expired locks
                for lock_id in expired_locks:
                    self.release_lock(lock_id)
                    self.logger.warning(f"Released expired lock: {lock_id}")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        return {
            "available_resources": {
                "cpu_cores": self.pool.cpu_cores,
                "gpu_slots": self.pool.gpu_slots,
                "memory_gb": self.pool.memory_gb,
                "disk_gb": self.pool.disk_gb,
                "network_bandwidth": self.pool.network_bandwidth
            },
            "active_locks": len(self.active_locks),
            "lock_queue": len(self.lock_queue),
            "dependency_graph_size": len(self.dependency_graph)
        }
    
    def get_lock_info(self, lock_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific lock"""
        if lock_id in self.active_locks:
            lock = self.active_locks[lock_id]
            return {
                "lock_id": lock.lock_id,
                "task_id": lock.task_id,
                "module": lock.module,
                "resources": {str(k): v for k, v in lock.resources.items()},
                "priority": lock.priority.name,
                "acquired_at": lock.acquired_at.isoformat(),
                "expires_at": lock.expires_at.isoformat(),
                "is_expired": lock.is_expired()
            }
        return None
    
    def extend_lock(self, lock_id: str, additional_seconds: int) -> bool:
        """Extend the timeout of an existing lock"""
        if lock_id in self.active_locks:
            lock = self.active_locks[lock_id]
            lock.extend_timeout(additional_seconds)
            self.logger.info(f"Extended lock {lock_id} by {additional_seconds} seconds")
            return True
        return False

# Global resource manager instance
resource_manager = ResourceManager()

class SimulationResourceManager:
    """
    Specialized resource manager for ISV simulations
    Handles switching between classical and neural MD based on resource availability
    """
    
    def __init__(self):
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)
        
        # Resource requirements for different simulation methods
        self.method_requirements = {
            "CLASSIC_MD": {
                ResourceType.CPU_CORE: 4,
                ResourceType.GPU_SLOT: 1,
                ResourceType.MEMORY_GB: 8
            },
            "NEURAL_MD": {
                ResourceType.CPU_CORE: 2,
                ResourceType.MEMORY_GB: 4
            }
        }
    
    async def choose_simulation_method(self, 
                                     task_id: str, 
                                     complexity: str = "MEDIUM",
                                     precision_required: str = "MEDIUM") -> str:
        """
        Choose simulation method based on resource availability and requirements
        
        Args:
            task_id: Task identifier
            complexity: Complexity level (LOW, MEDIUM, HIGH)
            precision_required: Required precision level (LOW, MEDIUM, HIGH)
            
        Returns:
            Chosen simulation method
        """
        # Default to neural MD
        preferred_method = "NEURAL_MD"
        
        # Prefer classical MD for high precision or low complexity
        if precision_required == "HIGH" or complexity == "LOW":
            preferred_method = "CLASSIC_MD"
        
        # Check if preferred method is available
        required_resources = self.method_requirements[preferred_method]
        
        lock_id = await self.resource_manager.acquire_lock(
            task_id=task_id,
            module="ISV_simulation",
            resources=required_resources,
            timeout_seconds=60,
            priority=LockPriority.HIGH
        )
        
        if lock_id:
            return preferred_method
        
        # Fallback to alternative method
        alternative_method = "NEURAL_MD" if preferred_method == "CLASSIC_MD" else "CLASSIC_MD"
        alternative_resources = self.method_requirements[alternative_method]
        
        fallback_lock_id = await self.resource_manager.acquire_lock(
            task_id=task_id,
            module="ISV_simulation",
            resources=alternative_resources,
            timeout_seconds=60,
            priority=LockPriority.NORMAL
        )
        
        if fallback_lock_id:
            self.logger.info(f"Fallback to {alternative_method} for task {task_id}")
            return alternative_method
        
        # If both fail, return neural MD (requires fewer resources)
        self.logger.warning(f"No resources available for preferred methods, using NEURAL_MD for task {task_id}")
        return "NEURAL_MD"
    
    async def acquire_simulation_resources(self, 
                                         task_id: str, 
                                         method: str,
                                         timeout_seconds: int = 3600) -> Optional[str]:
        """Acquire resources for a specific simulation method"""
        if method not in self.method_requirements:
            raise ValueError(f"Unknown simulation method: {method}")
        
        required_resources = self.method_requirements[method]
        
        return await self.resource_manager.acquire_lock(
            task_id=task_id,
            module="ISV_simulation",
            resources=required_resources,
            timeout_seconds=timeout_seconds,
            priority=LockPriority.HIGH
        )
    
    def release_simulation_resources(self, lock_id: str) -> bool:
        """Release simulation resources"""
        return self.resource_manager.release_lock(lock_id)

# Global simulation resource manager instance
simulation_resource_manager = SimulationResourceManager()
