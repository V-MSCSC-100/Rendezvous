-- HF Deluxe Pro Manager Database Schema
PRAGMA foreign_keys = ON;

-- 1. VEHICLES TABLE
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    manufacturer TEXT NOT NULL DEFAULT 'Hero',
    model TEXT NOT NULL DEFAULT 'HF Deluxe Pro',
    registration_number TEXT NOT NULL UNIQUE,
    purchase_date TEXT NOT NULL,
    purchase_price REAL NOT NULL DEFAULT 0.0,
    current_odometer REAL NOT NULL DEFAULT 0.0,
    engine_capacity REAL NOT NULL DEFAULT 97.2,
    fuel_type TEXT NOT NULL DEFAULT 'Petrol',
    notes TEXT DEFAULT '',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. REFUELS TABLE
CREATE TABLE IF NOT EXISTS refuels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    odometer REAL NOT NULL,
    fuel_quantity REAL NOT NULL,
    price_per_litre REAL NOT NULL,
    total_amount REAL NOT NULL,
    petrol_station TEXT DEFAULT '',
    is_full_tank INTEGER NOT NULL DEFAULT 1,
    calculated_mileage REAL DEFAULT NULL,
    distance_travelled REAL DEFAULT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. SERVICES TABLE
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_date TEXT NOT NULL,
    odometer REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    labour_charges REAL NOT NULL DEFAULT 0.0,
    parts_charges REAL NOT NULL DEFAULT 0.0,
    total_expenditure REAL NOT NULL DEFAULT 0.0,
    workshop_name TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. PARTS TABLE
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    part_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    total_price REAL NOT NULL DEFAULT 0.0,
    replacement_date TEXT NOT NULL,
    next_recommended_odometer REAL DEFAULT NULL,
    replacement_interval_km REAL DEFAULT NULL,
    replacement_interval_months INTEGER DEFAULT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. UPGRADES TABLE
CREATE TABLE IF NOT EXISTS upgrades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    upgrade_name TEXT NOT NULL,
    category TEXT DEFAULT 'Accessories',
    description TEXT DEFAULT '',
    installation_date TEXT NOT NULL,
    odometer REAL DEFAULT NULL,
    cost REAL NOT NULL DEFAULT 0.0,
    vendor TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. EXPENSES TABLE (Miscellaneous expenses)
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    expense_date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0.0,
    odometer REAL DEFAULT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. TRIPS TABLE
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    start_location TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Planned', -- Planned, Completed, Cancelled
    start_date TEXT NOT NULL,
    end_date TEXT DEFAULT '',
    is_round_trip INTEGER NOT NULL DEFAULT 0,
    estimated_distance REAL NOT NULL DEFAULT 0.0,
    estimated_duration REAL NOT NULL DEFAULT 0.0,
    assumed_mileage REAL NOT NULL DEFAULT 65.0,
    petrol_price_used REAL NOT NULL DEFAULT 102.0,
    estimated_fuel_litres REAL NOT NULL DEFAULT 0.0,
    estimated_fuel_cost REAL NOT NULL DEFAULT 0.0,
    estimated_cost_per_km REAL NOT NULL DEFAULT 0.0,
    actual_start_odometer REAL DEFAULT NULL,
    actual_end_odometer REAL DEFAULT NULL,
    actual_distance REAL DEFAULT NULL,
    actual_fuel_litres REAL DEFAULT NULL,
    actual_fuel_cost REAL DEFAULT NULL,
    toll_charges REAL NOT NULL DEFAULT 0.0,
    parking_charges REAL NOT NULL DEFAULT 0.0,
    additional_expenses REAL NOT NULL DEFAULT 0.0,
    actual_cost_per_km REAL DEFAULT NULL,
    actual_mileage REAL DEFAULT NULL,
    notes TEXT DEFAULT '',
    route_geometry_json TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. TRIP WAYPOINTS TABLE
CREATE TABLE IF NOT EXISTS trip_waypoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL,
    location_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    stop_type TEXT NOT NULL DEFAULT 'Stop', -- Start, Stop, Destination
    notes TEXT DEFAULT ''
);

-- 9. SAVED LOCATIONS TABLE
CREATE TABLE IF NOT EXISTS saved_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT DEFAULT '',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    category TEXT DEFAULT 'General',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. APP SETTINGS TABLE
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_refuels_vehicle_date ON refuels(vehicle_id, date);
CREATE INDEX IF NOT EXISTS idx_refuels_vehicle_odo ON refuels(vehicle_id, odometer);
CREATE INDEX IF NOT EXISTS idx_services_vehicle_date ON services(vehicle_id, service_date);
CREATE INDEX IF NOT EXISTS idx_parts_vehicle ON parts(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_parts_service ON parts(service_id);
CREATE INDEX IF NOT EXISTS idx_upgrades_vehicle ON upgrades(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_expenses_vehicle ON expenses(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_trips_vehicle ON trips(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_waypoints_trip ON trip_waypoints(trip_id, sequence_order);

