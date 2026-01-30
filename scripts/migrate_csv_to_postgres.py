"""Migrate CSV data to PostgreSQL database."""
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_database_url():
    """Get database URL from environment."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return db_url


def create_connection():
    """Create database connection."""
    db_url = get_database_url()
    print(f"Connecting to database...")
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise


def load_csv_data(csv_path='data/thrift_sales_12_weeks_with_subcategory.csv'):
    """Load data from CSV file."""
    print(f"Loading CSV data from {csv_path}...")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records from CSV")
    
    # Convert date columns
    df['production_date'] = pd.to_datetime(df['production_date'], errors='coerce')
    df['sold_date'] = pd.to_datetime(df['sold_date'], errors='coerce')
    
    # Replace NaN with None for SQL
    df = df.where(pd.notnull(df), None)
    
    return df


def migrate_data(conn, df):
    """Migrate data to PostgreSQL."""
    print("Starting data migration...")
    
    cursor = conn.cursor()
    
    try:
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM sales_data")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Database already contains {existing_count} records.")
            print("Clearing existing data for fresh load...")
            cursor.execute("TRUNCATE TABLE sales_data RESTART IDENTITY CASCADE")
            conn.commit()
        
        # Prepare insert statement
        insert_query = """
            INSERT INTO sales_data (
                item_id, department, category, subcategory, brand,
                production_date, sold_date, days_to_sell,
                production_price, sold_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Prepare data for batch insert
        records = []
        for _, row in df.iterrows():
            records.append((
                int(row['item_id']),
                row['department'],
                row['category'],
                row['subcategory'],
                row['brand'],
                row['production_date'],
                row['sold_date'],
                int(row['days_to_sell']) if pd.notna(row['days_to_sell']) else None,
                float(row['production_price']) if pd.notna(row['production_price']) else None,
                float(row['sold_price']) if pd.notna(row['sold_price']) else None
            ))
        
        # Batch insert
        print(f"Inserting {len(records)} records...")
        execute_batch(cursor, insert_query, records, page_size=1000)
        
        conn.commit()
        print(f"✅ Successfully migrated {len(records)} records to PostgreSQL")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM sales_data")
        final_count = cursor.fetchone()[0]
        print(f"Total records in database: {final_count}")
        
        # Show sample statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT brand) as brands,
                COUNT(DISTINCT category) as categories,
                COUNT(DISTINCT subcategory) as subcategories,
                COUNT(*) FILTER (WHERE sold_date IS NOT NULL) as sold_items
            FROM sales_data
        """)
        stats = cursor.fetchone()
        print(f"\n📊 Database Statistics:")
        print(f"  - Unique brands: {stats[0]}")
        print(f"  - Categories: {stats[1]}")
        print(f"  - Subcategories: {stats[2]}")
        print(f"  - Sold items: {stats[3]}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()


def main():
    """Main migration function."""
    try:
        # Load CSV data
        df = load_csv_data()
        
        # Create database connection
        conn = create_connection()
        
        # Migrate data
        migrate_data(conn, df)
        
        # Close connection
        conn.close()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
