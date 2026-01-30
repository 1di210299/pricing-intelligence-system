-- Create sales_data table
CREATE TABLE IF NOT EXISTS sales_data (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    department VARCHAR(50),
    category VARCHAR(50),
    subcategory VARCHAR(50),
    brand VARCHAR(100),
    production_date DATE,
    sold_date DATE,
    days_to_sell INTEGER,
    production_price DECIMAL(10, 2),
    sold_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for fast searching
CREATE INDEX IF NOT EXISTS idx_brand ON sales_data(brand);
CREATE INDEX IF NOT EXISTS idx_category ON sales_data(category);
CREATE INDEX IF NOT EXISTS idx_subcategory ON sales_data(subcategory);
CREATE INDEX IF NOT EXISTS idx_department ON sales_data(department);
CREATE INDEX IF NOT EXISTS idx_sold_date ON sales_data(sold_date) WHERE sold_date IS NOT NULL;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_sales_data_updated_at BEFORE UPDATE ON sales_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE sales_data TO pricing_user;
GRANT USAGE, SELECT ON SEQUENCE sales_data_id_seq TO pricing_user;
