import sqlite3
import sys
import os
import argparse
import logging

# Add the parent directory to Python path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("psycopg2 is required for PostgreSQL connections. Install it with 'pip install psycopg2-binary'.")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sqlite_tables(sqlite_conn):
    """Get all table names from SQLite database"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def get_table_schema(sqlite_conn, table_name):
    """Get the schema of a SQLite table"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def sqlite_to_pg_type(sqlite_type):
    """Convert SQLite data type to PostgreSQL data type"""
    sqlite_type = sqlite_type.upper()
    if 'INTEGER PRIMARY KEY' in sqlite_type:
        return 'SERIAL PRIMARY KEY'
    elif 'INTEGER' in sqlite_type:
        return 'INTEGER'
    elif 'TEXT' in sqlite_type:
        return 'TEXT'
    elif 'REAL' in sqlite_type:
        return 'REAL'
    elif 'BLOB' in sqlite_type:
        return 'BYTEA'
    elif 'BOOLEAN' in sqlite_type:
        return 'BOOLEAN'
    elif 'TIMESTAMP' in sqlite_type:
        return 'TIMESTAMP'
    else:
        return 'TEXT'  # Default to TEXT for unknown types

def get_foreign_keys(sqlite_conn, table_name):
    """Get foreign key constraints for a table"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    return cursor.fetchall()

def create_pg_table(pg_conn, table_name, schema, foreign_keys):
    """Create a PostgreSQL table based on SQLite schema"""
    cursor = pg_conn.cursor()
    
    # Build column definitions
    columns = []
    primary_key = None
    unique_constraints = []
    
    # First, identify all columns that need UNIQUE constraints
    # This includes columns referenced by foreign keys from other tables
    referenced_columns = set()
    
    # Check if we need to add UNIQUE constraints for foreign key references
    for fk in foreign_keys:
        fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
        referenced_columns.add((ref_table, to_col))
    
    # Special handling for users table - always ensure username is UNIQUE
    if table_name == 'users':
        for col in schema:
            if col[1] == 'username':
                referenced_columns.add(('users', 'username'))
    
    for col in schema:
        col_id, col_name, col_type, not_null, default_value, is_pk = col
        
        # Handle primary key
        if is_pk:
            if 'INTEGER' in col_type.upper():
                # For INTEGER PRIMARY KEY, use SERIAL PRIMARY KEY but keep the column name
                pg_type = 'SERIAL PRIMARY KEY'
                primary_key = col_name
                columns.append(f"\"{col_name}\" {pg_type}")
            else:
                pg_type = sqlite_to_pg_type(col_type)
                columns.append(f"\"{col_name}\" {pg_type} PRIMARY KEY")
                primary_key = col_name
        else:
            pg_type = sqlite_to_pg_type(col_type)
            column_def = f"\"{col_name}\" {pg_type}"
            
            # Add NOT NULL constraint if needed
            if not_null:
                column_def += " NOT NULL"
                
            # Add default value if exists
            if default_value is not None:
                if default_value == 'CURRENT_TIMESTAMP':
                    column_def += " DEFAULT CURRENT_TIMESTAMP"
                elif pg_type == 'BOOLEAN':
                    # Convert SQLite boolean representation to PostgreSQL
                    bool_val = 'TRUE' if default_value.upper() in ('1', 'TRUE') else 'FALSE'
                    column_def += f" DEFAULT {bool_val}"
                elif pg_type == 'TEXT':
                    # Properly escape single quotes in default values for PostgreSQL
                    escaped_value = default_value.replace("'", "''")
                    column_def += f" DEFAULT '{escaped_value}'"
                else:
                    column_def += f" DEFAULT {default_value}"
            
            # Add UNIQUE constraint if this column is referenced by a foreign key
            # or if it has a UNIQUE constraint in SQLite (indicated by "UNIQUE" in col_type)
            # or if it's the username column in the users table
            if 'UNIQUE' in col_type.upper() or (table_name, col_name) in referenced_columns or (table_name == 'users' and col_name == 'username'):
                column_def += " UNIQUE"
                    
            columns.append(column_def)
    
    # Create table SQL
    create_table_sql = f"CREATE TABLE IF NOT EXISTS \"{table_name}\" (" + "\n    " + ",\n    ".join(columns)
    
    # Add foreign key constraints
    fk_constraints = []
    for fk in foreign_keys:
        fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
        fk_constraint = f"FOREIGN KEY (\"{from_col}\") REFERENCES \"{ref_table}\"(\"{to_col}\")"  
        
        # Add ON DELETE clause if specified
        if on_delete:
            fk_constraint += f" ON DELETE {on_delete}"
            
        fk_constraints.append(fk_constraint)
    
    if fk_constraints:
        create_table_sql += ",\n    " + ",\n    ".join(fk_constraints)
    
    create_table_sql += "\n);"
    
    # Execute the CREATE TABLE statement
    try:
        cursor.execute(create_table_sql)
        logger.info(f"Created table {table_name} in PostgreSQL")
        
        # If this is the users table, ensure username has a unique constraint
        # This is a fallback in case the column definition didn't add it
        if table_name == 'users':
            try:
                cursor.execute('ALTER TABLE "users" ADD CONSTRAINT users_username_key UNIQUE (username);')
                logger.info("Added unique constraint to username column in users table")
            except Exception as e:
                # If the constraint already exists, this is fine
                if 'already exists' not in str(e):
                    logger.warning(f"Note: Could not add unique constraint to username: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {str(e)}")
        logger.error(f"SQL: {create_table_sql}")
        raise

def copy_table_data(sqlite_conn, pg_conn, table_name, schema):
    """Copy data from SQLite table to PostgreSQL table"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Get column names
    column_names = [col[1] for col in schema]
    
    # Check if table has a SERIAL/AUTOINCREMENT primary key
    has_serial_pk = False
    pk_column = None
    for col in schema:
        if col[5] and 'INTEGER' in col[2].upper():  # is_pk and type contains INTEGER
            has_serial_pk = True
            pk_column = col[1]
            break
    
    # If table has a SERIAL primary key, exclude it from the INSERT
    if has_serial_pk:
        column_names.remove(pk_column)
    
    # Fetch all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        logger.info(f"No data to copy for table {table_name}")
        return
    
    # Prepare column list for INSERT statement
    columns_str = '", "'.join(column_names)
    
    # Prepare placeholders for INSERT statement
    placeholders = ', '.join(['%s'] * len(column_names))
    
    # Set autocommit mode before starting transaction
    original_autocommit = pg_conn.autocommit
    pg_conn.autocommit = False
    
    try:
        # Insert data in batches
        batch_size = 100
        total_rows = len(rows)
        
        for i in range(0, total_rows, batch_size):
            batch = rows[i:i+batch_size]
            batch_values = []
            
            for row in batch:
                # If we're skipping the primary key, adjust the row data
                row_values = list(row)
                
                if has_serial_pk:
                    pk_index = next(idx for idx, col in enumerate(schema) if col[1] == pk_column)
                    row_values.pop(pk_index)
                
                # Convert SQLite boolean integers to PostgreSQL booleans
                for i, col in enumerate(schema):
                    col_name = col[1]
                    col_type = col[2].upper()
                    
                    # Skip the primary key column if it's being excluded
                    if has_serial_pk and col_name == pk_column:
                        continue
                    
                    # Adjust index if primary key was removed
                    adj_i = i if not has_serial_pk else (i if i < pk_index else i - 1)
                    
                    # Convert integer booleans to actual booleans
                    if 'BOOLEAN' in col_type and row_values[adj_i] is not None:
                        row_values[adj_i] = bool(row_values[adj_i])
                
                batch_values.append(tuple(row_values))
            
            # Execute batch insert
            insert_sql = f'INSERT INTO "{table_name}" ("{columns_str}") VALUES ({placeholders})'
            pg_cursor.executemany(insert_sql, batch_values)
            
            logger.info(f"Inserted {len(batch)} rows into {table_name} ({i+len(batch)}/{total_rows})")
        
        # Commit transaction
        pg_conn.commit()
        logger.info(f"Successfully copied all data for table {table_name}")
    except Exception as e:
        pg_conn.rollback()
        logger.error(f"Error copying data for table {table_name}: {str(e)}")
        raise
    finally:
        # Restore original autocommit setting
        pg_conn.autocommit = original_autocommit

def migrate_database(sqlite_path, pg_host, pg_port, pg_user, pg_password, pg_db, drop_existing=False):
    """Migrate data from SQLite to PostgreSQL"""
    # Connect to SQLite database
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite database: {sqlite_path}")
    except Exception as e:
        logger.error(f"Error connecting to SQLite database: {str(e)}")
        return False
    
    # Connect to PostgreSQL database
    try:
        pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user=pg_user,
            password=pg_password,
            database=pg_db
        )
        # Set autocommit to True initially to avoid transaction issues
        pg_conn.autocommit = True
        logger.info(f"Connected to PostgreSQL database: {pg_db} on {pg_host}")
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL database: {str(e)}")
        sqlite_conn.close()
        return False
        
    # Drop existing tables if requested
    if drop_existing:
        try:
            cursor = pg_conn.cursor()
            # Get all tables from SQLite to know what to drop
            tables = get_sqlite_tables(sqlite_conn)
            
            # Disable foreign key checks temporarily
            cursor.execute("SET session_replication_role = 'replica';")
            
            # Drop tables in reverse order to handle dependencies
            for table_name in reversed(tables):
                logger.info(f"Dropping table {table_name} if exists")
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
                
            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = 'origin';")
            logger.info("Dropped existing tables")
        except Exception as e:
            logger.error(f"Error dropping existing tables: {str(e)}")
            return False
    
    try:
        # Get all tables from SQLite
        tables = get_sqlite_tables(sqlite_conn)
        logger.info(f"Found {len(tables)} tables in SQLite database: {', '.join(tables)}")
        
        # Create a custom order for tables to ensure proper foreign key references
        # We need to ensure 'users' table is created first since it's referenced by other tables
        ordered_tables = []
        
        # First, add the 'users' table if it exists
        if 'users' in tables:
            ordered_tables.append('users')
            
        # Then add tables that don't have foreign keys or don't reference other tables
        for table_name in tables:
            if table_name != 'users' and table_name != 'sqlite_sequence':
                foreign_keys = get_foreign_keys(sqlite_conn, table_name)
                if not foreign_keys:
                    ordered_tables.append(table_name)
        
        # Finally add tables with foreign keys
        for table_name in tables:
            if table_name not in ordered_tables and table_name != 'sqlite_sequence':
                ordered_tables.append(table_name)
                
        # Add sqlite_sequence last if it exists
        if 'sqlite_sequence' in tables:
            ordered_tables.append('sqlite_sequence')
            
        logger.info(f"Table processing order: {', '.join(ordered_tables)}")
        
        # Process each table in the correct order
        for table_name in ordered_tables:
            logger.info(f"Processing table: {table_name}")
            
            # Get table schema and foreign keys
            schema = get_table_schema(sqlite_conn, table_name)
            foreign_keys = get_foreign_keys(sqlite_conn, table_name)
            
            # Special handling for users table to ensure username has UNIQUE constraint
            if table_name == 'users':
                # Find the username column and ensure it has UNIQUE constraint
                for i, col in enumerate(schema):
                    if col[1] == 'username':
                        # Add UNIQUE to the column type if not already present
                        if 'UNIQUE' not in col[2].upper():
                            schema_list = list(schema[i])
                            schema_list[2] = schema_list[2] + ' UNIQUE'
                            schema[i] = tuple(schema_list)
            
            # Create table in PostgreSQL
            create_pg_table(pg_conn, table_name, schema, foreign_keys)
            
            # Copy data
            copy_table_data(sqlite_conn, pg_conn, table_name, schema)
        
        logger.info("Migration completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False
    finally:
        sqlite_conn.close()
        pg_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite database to PostgreSQL')
    parser.add_argument('--sqlite', required=True, help='Path to SQLite database file')
    parser.add_argument('--pg-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--pg-port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--pg-user', required=True, help='PostgreSQL username')
    parser.add_argument('--pg-password', required=True, help='PostgreSQL password')
    parser.add_argument('--pg-db', required=True, help='PostgreSQL database name')
    parser.add_argument('--drop-existing', action='store_true', help='Drop existing tables before migration')
    
    args = parser.parse_args()
    
    print("Starting database migration from SQLite to PostgreSQL...")
    success = migrate_database(
        args.sqlite,
        args.pg_host,
        args.pg_port,
        args.pg_user,
        args.pg_password,
        args.pg_db,
        args.drop_existing
    )
    
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()