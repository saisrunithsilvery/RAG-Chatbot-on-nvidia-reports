import os
import json
import time
import redis
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from loguru import logger


class RedisManager:
    """Utility class for Redis operations including streams"""
    
    def __init__(self):
        """Initialize Redis connection"""
        # Set up Redis connection
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True  # Auto-decode Redis responses to strings
            )
            # Test connection
            self.redis.ping()
            self.connected = True
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            self.connected = False
            logger.warning(f"Could not connect to Redis at {redis_host}:{redis_port}: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if connected to Redis"""
        if not hasattr(self, 'connected') or not self.connected:
            return False
        
        try:
            self.redis.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis"""
        if not self.is_connected():
            return None
        
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    def set(self, key: str, value: str, expiry: Optional[int] = None) -> bool:
        """Set a value in Redis with optional expiry in seconds"""
        if not self.is_connected():
            return False
        
        try:
            if expiry:
                return self.redis.set(key, value, ex=expiry)
            else:
                return self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    def json_get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a JSON value from Redis"""
        if not self.is_connected():
            return None
        
        try:
            data = self.redis.get(key)
            if not data:
                return None
            return json.loads(data)
        except Exception as e:
            logger.error(f"Redis json_get error: {str(e)}")
            return None
    
    def json_set(self, key: str, value: Dict[str, Any], expiry: Optional[int] = None) -> bool:
        """Set a JSON value in Redis with optional expiry in seconds"""
        if not self.is_connected():
            return False
        
        try:
            json_data = json.dumps(value)
            if expiry:
                return self.redis.set(key, json_data, ex=expiry)
            else:
                return self.redis.set(key, json_data)
        except Exception as e:
            logger.error(f"Redis json_set error: {str(e)}")
            return False
    
    def stream_add(self, stream_name: str, data: Dict[str, Any], max_len: int = 1000) -> Optional[str]:
        """
        Add a message to a Redis stream
        
        Args:
            stream_name: Name of the stream
            data: Dictionary of field-value pairs to add
            max_len: Maximum length of the stream
            
        Returns:
            Message ID or None if failed
        """
        if not self.is_connected():
            return None
        
        try:
            # Convert all values to strings
            string_data = {k: str(v) for k, v in data.items()}
            
            # Add to stream with trimming
            return self.redis.xadd(
                name=stream_name,
                fields=string_data,
                maxlen=max_len,
                approximate=True
            )
        except Exception as e:
            logger.error(f"Redis stream_add error: {str(e)}")
            return None
    
    def stream_read(self, stream_name: str, count: int = 10, block: Optional[int] = None, 
                   last_id: str = '0-0') -> List[Dict[str, Any]]:
        """
        Read messages from a Redis stream
        
        Args:
            stream_name: Name of the stream
            count: Maximum number of messages to read
            block: If specified, block for this many milliseconds if no messages available
            last_id: ID to start reading from (0-0 for beginning, $ for end)
            
        Returns:
            List of messages as dictionaries
        """
        if not self.is_connected():
            return []
        
        try:
            # Read from stream
            response = self.redis.xread(
                streams={stream_name: last_id},
                count=count,
                block=block
            )
            
            # Process response
            messages = []
            for stream_data in response:
                stream, stream_messages = stream_data
                for message_id, fields in stream_messages:
                    messages.append({
                        'id': message_id,
                        'data': fields
                    })
            
            return messages
        except Exception as e:
            logger.error(f"Redis stream_read error: {str(e)}")
            return []
    
    def stream_create_consumer_group(self, stream_name: str, group_name: str, 
                                    start_id: str = '$', mkstream: bool = True) -> bool:
        """
        Create a consumer group for a stream
        
        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            start_id: ID to start consuming from (0 for beginning, $ for end)
            mkstream: Create the stream if it doesn't exist
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            # Check if group already exists
            try:
                groups = self.redis.xinfo_groups(stream_name)
                for group in groups:
                    if group.get('name') == group_name:
                        logger.info(f"Consumer group '{group_name}' already exists for stream '{stream_name}'")
                        return True
            except redis.ResponseError:
                # Stream doesn't exist yet, will be created if mkstream=True
                pass
            
            # Create consumer group
            self.redis.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id=start_id,
                mkstream=mkstream
            )
            logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
            return True
        except Exception as e:
            logger.error(f"Redis stream_create_consumer_group error: {str(e)}")
            


# Configure logging
logger = logging.getLogger(__name__)

def get_redis_connection():
    """
    Returns a connection to the Redis server.
    
    Returns:
        redis.Redis: A Redis client connection
    """
    try:
        # Get Redis configuration from environment variables or use defaults
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        
        # Log connection attempt
        logger.info(f"Attempting to connect to Redis at {redis_host}:{redis_port} (DB: {redis_db})")
        
        # Create and return the Redis connection
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True  # Automatically decode responses to Python strings
        )
        
        # Test the connection
        redis_client.ping()
        logger.info("Redis connection successful")
        
        return redis_client
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        # Return a dummy Redis client that logs operations instead of failing
        return DummyRedisClient()
    except Exception as e:
        logger.error(f"Error setting up Redis: {str(e)}")
        # Return a dummy Redis client that logs operations instead of failing
        return DummyRedisClient()

class DummyRedisClient:
    """A dummy Redis client that logs operations instead of actually connecting to Redis"""
    
    def __init__(self):
        self.data = {}
        logger.warning("Using dummy Redis client - no actual Redis connection")
    
    def get(self, key):
        logger.info(f"Dummy Redis - GET operation for key: {key}")
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        logger.info(f"Dummy Redis - SET operation for key: {key}")
        self.data[key] = value
        return True
    
    def delete(self, key):
        logger.info(f"Dummy Redis - DELETE operation for key: {key}")
        if key in self.data:
            del self.data[key]
        return 1
    
    def ping(self):
        logger.info("Dummy Redis - PING operation")
        return True
