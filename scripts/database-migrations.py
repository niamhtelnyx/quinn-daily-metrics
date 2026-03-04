#!/usr/bin/env python3
"""
Database Migration Framework
Handles schema changes with versioned migrations for API integration projects
"""

import os
import sqlite3
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationManager:
    def __init__(self, db_path: str, migrations_dir: str = None):
        """Initialize migration manager"""
        self.db_path = db_path
        self.migrations_dir = migrations_dir or os.path.join(os.path.dirname(db_path), 'migrations')
        Path(self.migrations_dir).mkdir(exist_ok=True)
        self.setup_migrations_table()
    
    def setup_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum TEXT
        )
        """)
        conn.commit()
        conn.close()
        logger.info("Migration tracking table ready")
    
    def get_current_version(self) -> str:
        """Get the latest applied migration version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "000"
    
    def get_pending_migrations(self) -> list:
        """Get list of pending migrations to apply"""
        applied_migrations = set()
        
        # Get applied migrations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT version FROM schema_migrations")
        applied_migrations = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        # Get all migration files
        migration_files = []
        for file in os.listdir(self.migrations_dir):
            if file.endswith('.sql') and '_' in file:
                version = file.split('_')[0]
                if version not in applied_migrations:
                    migration_files.append((version, file))
        
        # Sort by version
        return sorted(migration_files)
    
    def create_migration(self, name: str) -> str:
        """Create a new migration file"""
        # Generate version (timestamp)
        version = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Clean name for filename
        clean_name = name.lower().replace(' ', '_').replace('-', '_')
        filename = f"{version}_{clean_name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)
        
        # Create migration file with template
        template = f"""-- Migration: {name}
-- Version: {version}
-- Created: {datetime.now().isoformat()}

-- Add your migration SQL here
-- Example:
-- CREATE TABLE example_table (
--     id INTEGER PRIMARY KEY,
--     name TEXT NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Add indexes
-- CREATE INDEX idx_example_name ON example_table(name);

-- Migration complete
"""
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration: {filename}")
        return filepath
    
    def apply_migration(self, version: str, filename: str) -> bool:
        """Apply a single migration"""
        filepath = os.path.join(self.migrations_dir, filename)
        
        if not os.path.exists(filepath):
            logger.error(f"Migration file not found: {filepath}")
            return False
        
        try:
            # Read migration SQL
            with open(filepath, 'r') as f:
                migration_sql = f.read()
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.md5(migration_sql.encode()).hexdigest()
            
            # Apply migration
            conn = sqlite3.connect(self.db_path)
            
            # Execute migration (handle multiple statements)
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement and not statement.startswith('--'):
                    conn.execute(statement)
            
            # Record migration
            name = filename.replace('.sql', '').replace(f'{version}_', '').replace('_', ' ').title()
            conn.execute(
                "INSERT INTO schema_migrations (version, name, checksum) VALUES (?, ?, ?)",
                (version, name, checksum)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Applied migration: {version} - {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            return False
    
    def migrate(self) -> bool:
        """Apply all pending migrations"""
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Applying {len(pending)} migration(s)")
        
        success_count = 0
        for version, filename in pending:
            if self.apply_migration(version, filename):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping at {version}")
                break
        
        logger.info(f"Applied {success_count}/{len(pending)} migrations")
        return success_count == len(pending)
    
    def rollback_to(self, target_version: str):
        """Rollback to a specific version (destructive!)"""
        logger.warning(f"Rollback to {target_version} - THIS IS DESTRUCTIVE!")
        
        # Get migrations to rollback
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT version, name FROM schema_migrations WHERE version > ? ORDER BY version DESC",
            (target_version,)
        )
        to_rollback = cursor.fetchall()
        
        if not to_rollback:
            logger.info("No migrations to rollback")
            return True
        
        # Note: SQLite doesn't support easy rollbacks
        # This is a simple approach - delete migration records
        # Real rollbacks would need custom rollback scripts
        for version, name in to_rollback:
            conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
            logger.warning(f"Removed migration record: {version} - {name}")
            logger.warning("Note: This only removes the record, not the schema changes!")
        
        conn.commit()
        conn.close()
        
        logger.warning("Rollback complete - Manual schema cleanup may be needed")
        return True
    
    def status(self):
        """Show migration status"""
        current_version = self.get_current_version()
        pending = self.get_pending_migrations()
        
        print(f"📊 Migration Status")
        print(f"   Database: {self.db_path}")
        print(f"   Current Version: {current_version}")
        print(f"   Pending Migrations: {len(pending)}")
        
        if pending:
            print("\n🔄 Pending Migrations:")
            for version, filename in pending:
                name = filename.replace('.sql', '').replace(f'{version}_', '').replace('_', ' ').title()
                print(f"   • {version}: {name}")
        else:
            print("\n✅ All migrations applied")
        
        # Show applied migrations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT version, name, executed_at FROM schema_migrations ORDER BY version DESC LIMIT 5"
        )
        applied = cursor.fetchall()
        conn.close()
        
        if applied:
            print("\n📝 Recent Applied Migrations:")
            for version, name, executed_at in applied:
                print(f"   • {version}: {name} ({executed_at})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 database-migrations.py <command> [args]")
        print("Commands:")
        print("  status <db_path>                 - Show migration status")
        print("  create <db_path> <name>          - Create new migration")
        print("  migrate <db_path>                - Apply pending migrations")
        print("  rollback <db_path> <version>     - Rollback to version (destructive)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status" and len(sys.argv) >= 3:
        db_path = sys.argv[2]
        manager = MigrationManager(db_path)
        manager.status()
        
    elif command == "create" and len(sys.argv) >= 4:
        db_path = sys.argv[2]
        name = " ".join(sys.argv[3:])
        manager = MigrationManager(db_path)
        filepath = manager.create_migration(name)
        print(f"Created migration: {filepath}")
        print("Edit the file and run 'migrate' to apply")
        
    elif command == "migrate" and len(sys.argv) >= 3:
        db_path = sys.argv[2]
        manager = MigrationManager(db_path)
        success = manager.migrate()
        sys.exit(0 if success else 1)
        
    elif command == "rollback" and len(sys.argv) >= 4:
        db_path = sys.argv[2]
        target_version = sys.argv[3]
        manager = MigrationManager(db_path)
        manager.rollback_to(target_version)
        
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)


if __name__ == "__main__":
    main()