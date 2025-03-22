import redis
import json
import os
import uuid
import streamlit as st
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("redis_helper")

# Redis Manager singleton
redis_client = None
REDIS_AVAILABLE = False

def initialize_redis():
    """Initialize Redis connection"""
    global redis_client, REDIS_AVAILABLE
    
    try:
        # Get Redis configuration from environment variables or use defaults
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        redis_url = os.getenv('REDIS_URL', f'redis://{redis_host}:{redis_port}/{redis_db}')
        
        logger.info(f"Attempting to connect to Redis at {redis_url}")
        
        # Create Redis connection
        if redis_password:
            redis_client = redis.Redis.from_url(redis_url, password=redis_password, decode_responses=True)
        else:
            redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        redis_client.ping()
        REDIS_AVAILABLE = True
        logger.info("Successfully connected to Redis")
        
        return True
    except Exception as e:
        redis_client = None
        REDIS_AVAILABLE = False
        logger.error(f"Redis connection failed: {str(e)}")
        return False

# Initialize Redis on module import
initialize_redis()

def get_session_id():
    """
    Get or create a unique session ID for the current user session
    """
    if 'redis_session_id' not in st.session_state:
        st.session_state.redis_session_id = str(uuid.uuid4())
        logger.info(f"Created new session ID: {st.session_state.redis_session_id}")
    
    return st.session_state.redis_session_id

def set_db_info(db_name, collection_name=None):
    """
    Store database connection info in Redis
    Only allows 'pinecone' or 'chromadb' as valid DB values.
    """
    global redis_client, REDIS_AVAILABLE
    
    # Validate that db_name is only pinecone or chromadb
    if not db_name:
        logger.warning("Attempted to store empty db_name")
        return False
        
    # Enforce valid DB types
    if db_name not in ['pinecone', 'chromadb']:
        logger.warning(f"Invalid database type: {db_name}. Only 'pinecone' or 'chromadb' are allowed.")
        return False
    
    # Print debug info
    logger.info(f"SET_DB_INFO CALLED: db_name={db_name}, collection_name={collection_name}")
    
    # Always update session state
    st.session_state.selected_db = db_name
    st.session_state.collection_name = collection_name
    
    # If Redis is available, also store there
    if REDIS_AVAILABLE and redis_client:
        try:
            session_id = get_session_id()
            
            db_info = {
                'db': db_name,
                'collection_name': collection_name
            }
            
            # Convert to JSON explicitly
            json_data = json.dumps(db_info)
            logger.info(f"Storing JSON in Redis: {json_data}")
            
            # Store in Redis with 24-hour expiration (86400 seconds)
            key = f"session:{session_id}:db_info"
            result = redis_client.setex(key, 86400, json_data)
            logger.info(f"Redis SETEX result: {result}")
            
            # Verify immediately
            verification = redis_client.get(key)
            logger.info(f"Verification check: {verification}")
            
            if verification:
                parsed = json.loads(verification)
                logger.info(f"Parsed verification: {parsed}")
                if parsed.get('db') != db_name:
                    logger.warning("WARNING: Verification mismatch on db field!")
            
            return True
        except Exception as e:
            logger.error(f"Error setting Redis db info: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.info("Redis not available for set_db_info, using session state only")
    
    return False

def get_db_info():
    """
    Retrieve database connection info from Redis or session state
    Ensures only valid DB types ('pinecone' or 'chromadb') are used
    """
    global redis_client, REDIS_AVAILABLE
    
    # Print debug info
    logger.info(f"GET_DB_INFO CALLED, session state: db={st.session_state.get('selected_db')}, collection={st.session_state.get('collection_name')}")
    
    db_info = None
    
    # Try Redis first if available
    if REDIS_AVAILABLE and redis_client:
        try:
            session_id = get_session_id()
            key = f"session:{session_id}:db_info"
            db_info_json = redis_client.get(key)
            
            logger.info(f"Redis GET result for {key}: {db_info_json}")
            
            if db_info_json:
                try:
                    db_info = json.loads(db_info_json)
                    logger.info(f"Parsed DB info from Redis: {db_info}")
                    
                    # Safety check - ensure both fields exist and db is valid
                    needs_repair = False
                    
                    # Check if db field is missing or null
                    if 'db' not in db_info or db_info['db'] is None:
                        logger.warning("WARNING: 'db' field missing or null in Redis data")
                        needs_repair = True
                    # Check if db is not a valid type
                    elif db_info['db'] not in ['pinecone', 'chromadb']:
                        logger.warning(f"WARNING: Invalid db type in Redis: {db_info['db']}")
                        # Default to chromadb
                        db_info['db'] = 'chromadb'
                        needs_repair = True
                    
                    # Attempt to repair if needed
                    if needs_repair:
                        if 'selected_db' in st.session_state and st.session_state.selected_db in ['pinecone', 'chromadb']:
                            logger.info(f"Attempting to repair Redis data with session state db: {st.session_state.selected_db}")
                            db_info['db'] = st.session_state.selected_db
                        else:
                            # Default to chromadb if no valid value in session state
                            logger.info("Defaulting to chromadb for repair")
                            db_info['db'] = 'chromadb'
                        
                        # Save the repaired data back to Redis
                        redis_client.setex(key, 86400, json.dumps(db_info))
                    
                    # Update session state for consistency
                    if db_info.get('db'):
                        st.session_state.selected_db = db_info.get('db')
                    if db_info.get('collection_name'):
                        st.session_state.collection_name = db_info.get('collection_name')
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from Redis: {e}")
            else:
                logger.info(f"No DB info found in Redis with key: {key}")
        except Exception as e:
            logger.error(f"Error getting Redis db info: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.info("Redis not available for get_db_info, using session state only")
    
    # If not in Redis but in session state, validate and save to Redis for next time
    if (not db_info or not db_info.get('db')) and 'selected_db' in st.session_state:
        # Validate session state db value
        db_value = st.session_state.selected_db
        if db_value not in ['pinecone', 'chromadb']:
            logger.warning(f"Invalid db type in session state: {db_value}. Defaulting to chromadb.")
            db_value = 'chromadb'
            st.session_state.selected_db = db_value
        
        logger.info(f"Using values from session state: db={db_value}, collection={st.session_state.collection_name if 'collection_name' in st.session_state else None}")
        
        db_info = {
            'db': db_value,
            'collection_name': st.session_state.collection_name if 'collection_name' in st.session_state else None
        }
        
        # Try to save back to Redis if available
        if REDIS_AVAILABLE and redis_client:
            try:
                set_db_info(db_info['db'], db_info['collection_name'])
            except Exception as e:
                logger.error(f"Failed to save session state back to Redis: {str(e)}")
    
    return db_info

def force_sync_session_with_redis():
    """Force synchronization between Redis and session state with DB type validation"""
    global redis_client, REDIS_AVAILABLE
    
    if REDIS_AVAILABLE and redis_client:
        try:
            # First, check if we have DB info in session state
            if 'selected_db' in st.session_state and st.session_state.selected_db:
                # Validate DB type
                db_value = st.session_state.selected_db
                if db_value not in ['pinecone', 'chromadb']:
                    logger.warning(f"Invalid db type in session state during sync: {db_value}. Defaulting to chromadb.")
                    db_value = 'chromadb'
                    st.session_state.selected_db = db_value
                
                # Save session state to Redis
                set_db_info(db_value, st.session_state.collection_name if 'collection_name' in st.session_state else None)
                
            # Then try to get from Redis
            session_id = get_session_id()
            key = f"session:{session_id}:db_info"
            db_info_json = redis_client.get(key)
            
            if db_info_json:
                db_info = json.loads(db_info_json)
                
                # Validate the db value from Redis
                if 'db' in db_info and db_info['db'] not in ['pinecone', 'chromadb']:
                    logger.warning(f"Invalid db type in Redis during sync: {db_info['db']}. Defaulting to chromadb.")
                    db_info['db'] = 'chromadb'
                    # Save the corrected value back to Redis
                    redis_client.setex(key, 86400, json.dumps(db_info))
                
                # Update session state
                st.session_state.selected_db = db_info.get('db')
                st.session_state.collection_name = db_info.get('collection_name')
                return True
                
        except Exception as e:
            logger.error(f"Error syncing with Redis: {str(e)}")
    
    return False

def repair_db_info():
    """
    Attempt to repair database info in Redis if it's inconsistent
    Ensures only valid DB types ('pinecone' or 'chromadb') are used
    """
    global redis_client, REDIS_AVAILABLE
    
    if not REDIS_AVAILABLE or not redis_client:
        return False
        
    try:
        session_id = get_session_id()
        key = f"session:{session_id}:db_info"
        
        # First check session state and validate
        if 'selected_db' in st.session_state and st.session_state.selected_db:
            db_value = st.session_state.selected_db
            if db_value not in ['pinecone', 'chromadb']:
                logger.warning(f"Invalid db type in session state during repair: {db_value}. Defaulting to chromadb.")
                db_value = 'chromadb'
                st.session_state.selected_db = db_value
        else:
            logger.info("No DB in session state to repair with")
            # Set default value
            db_value = 'chromadb'
            st.session_state.selected_db = db_value
            
        # Check what's in Redis
        db_info_json = redis_client.get(key)
        if db_info_json:
            try:
                db_info = json.loads(db_info_json)
                needs_repair = False
                
                # Check if db is missing or invalid
                if 'db' not in db_info or not db_info['db']:
                    db_info['db'] = db_value
                    needs_repair = True
                elif db_info['db'] not in ['pinecone', 'chromadb']:
                    db_info['db'] = db_value
                    needs_repair = True
                    
                # Save repaired data if needed
                if needs_repair:
                    redis_client.setex(key, 86400, json.dumps(db_info))
                    logger.info(f"Repaired Redis data with valid db: {db_value}")
                    return True
            except Exception as e:
                logger.error(f"Error parsing Redis data: {str(e)}")
                
        # If no data or couldn't repair, set from session state
        set_db_info(db_value, st.session_state.collection_name if 'collection_name' in st.session_state else None)
        return True
    except Exception as e:
        logger.error(f"Error repairing Redis db info: {str(e)}")
    
    return False

def debug_redis_status():
    """
    Return debug information about Redis connection and stored values
    For troubleshooting purposes
    """
    global redis_client, REDIS_AVAILABLE
    
    status = {
        "redis_available": REDIS_AVAILABLE,
        "redis_url": os.getenv('REDIS_URL', 'redis://localhost:6379'),
        "session_id": get_session_id(),
        "session_state_db": st.session_state.get("selected_db"),
        "session_state_collection": st.session_state.get("collection_name")
    }
    
    if REDIS_AVAILABLE and redis_client:
        try:
            session_id = get_session_id()
            key = f"session:{session_id}:db_info"
            db_info_json = redis_client.get(key)
            status["redis_key"] = key
            status["raw_redis_value"] = db_info_json if db_info_json else None
            
            if db_info_json:
                try:
                    status["parsed_value"] = json.loads(db_info_json)
                except json.JSONDecodeError:
                    status["json_error"] = "Could not parse JSON from Redis"
            
            # List all keys for this session
            all_session_keys = redis_client.keys(f"session:{session_id}:*")
            status["all_session_keys"] = all_session_keys
            
            # Test connection again
            redis_client.ping()
            status["connection_test"] = "successful"
        except Exception as e:
            status["error"] = str(e)
    
    return status

def display_debug_info():
    """
    Display Redis debug information in the Streamlit UI
    With additional validation for DB types
    """
    debug_info = debug_redis_status()
    
    with st.expander("Redis Debug Information", expanded=False):
        st.json(debug_info)
        
        if debug_info.get("redis_available"):
            if debug_info.get("parsed_value"):
                db_value = debug_info.get("parsed_value", {}).get("db")
                
                if not db_value:
                    st.warning("⚠️ DB field is missing in Redis data")
                    needs_repair = True
                elif db_value not in ['pinecone', 'chromadb']:
                    st.warning(f"⚠️ Invalid DB type in Redis: '{db_value}'. Only 'pinecone' or 'chromadb' are allowed.")
                    needs_repair = True
                else:
                    st.success(f"✅ Redis connection successful with valid DB type: '{db_value}'")
                    needs_repair = False
                
                if needs_repair:
                    if st.button("Repair Redis Data"):
                        if repair_db_info():
                            st.success("✅ Redis data repaired successfully")
                            st.rerun()
                        else:
                            st.error("❌ Failed to repair Redis data")
            else:
                st.warning("⚠️ Redis connected but no DB info found")
                if st.button("Initialize Redis Data"):
                    if 'selected_db' in st.session_state and st.session_state.selected_db:
                        # Validate DB type
                        db_value = st.session_state.selected_db
                        if db_value not in ['pinecone', 'chromadb']:
                            st.warning(f"Invalid db type: {db_value}. Defaulting to chromadb.")
                            db_value = 'chromadb'
                        
                        set_db_info(db_value, st.session_state.collection_name)
                        st.success("✅ Redis data initialized")
                        st.rerun()
                    else:
                        # Initialize with default value
                        set_db_info('chromadb', None)
                        st.success("✅ Redis initialized with default DB type: 'chromadb'")
                        st.rerun()
        else:
            st.error("❌ Redis connection failed")
            
        # Show session state
        st.write("Session State:")
        session_db = st.session_state.get("selected_db")
        if session_db and session_db not in ['pinecone', 'chromadb']:
            st.warning(f"⚠️ Invalid DB type in session state: '{session_db}'")
        
        st.write({
            "selected_db": session_db,
            "collection_name": st.session_state.get("collection_name")
        })
        
        # Manually set Redis data
        with st.expander("Manually Set Redis Data"):
            # Use selectbox instead of text_input to enforce valid options
            manual_db = st.selectbox(
                "Database type:",
                options=["pinecone", "chromadb"],
                index=0 if st.session_state.get("selected_db") == "pinecone" else 1
            )
            manual_collection = st.text_input("Collection name:", st.session_state.get("collection_name", ""))
            
            if st.button("Update Redis"):
                if set_db_info(manual_db, manual_collection):
                    st.success(f"✅ Redis data updated with DB: {manual_db}")
                    st.rerun()
                else:
                    st.error("❌ Failed to update Redis data")