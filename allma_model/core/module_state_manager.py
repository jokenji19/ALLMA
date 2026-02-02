"""
ModuleStateManager - Centralized persistence for ALLMA modules
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional
import os

class ModuleStateManager:
    """
    Manages persistence for ALLMA learning modules using SQLite.
    Stores state as JSON blobs indexed by module name.
    """
    
    def __init__(self, db_path: str = "allma_modules.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the database table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS module_states (
                        module_name TEXT PRIMARY KEY,
                        state_json TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logging.error(f"Failed to init module DB: {e}")

    def save_state(self, module_name: str, state: Dict[str, Any]) -> bool:
        """
        Save a module's state to the database.
        
        Args:
            module_name: Unique identifier for the module
            state: Dictionary containing serializable state data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_str = json.dumps(state)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO module_states (module_name, state_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (module_name, json_str))
                conn.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to save state for {module_name}: {e}")
            return False

    def load_state(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a module's state from the database.
        
        Args:
            module_name: Unique identifier for the module
            
        Returns:
            State dictionary if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT state_json FROM module_states WHERE module_name = ?", 
                    (module_name,)
                )
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                return None
        except Exception as e:
            logging.error(f"Failed to load state for {module_name}: {e}")
            return None
