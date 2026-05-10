-- Dealership Creative Automation — SQLite schema + seed data
-- Import: sqlite3 backend/data/app.db < database.sql
-- Or use the FastAPI app: tables are created on startup and the first run seeds the same data if empty.

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS creative_outputs;
DROP TABLE IF EXISTS creative_jobs;
DROP TABLE IF EXISTS dealerships;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS users;

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(64) NOT NULL UNIQUE,
    logo_path VARCHAR(512)
);

CREATE TABLE dealerships (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    address_line VARCHAR(512) NOT NULL DEFAULT '',
    phone VARCHAR(64) NOT NULL DEFAULT '',
    website VARCHAR(255) NOT NULL DEFAULT '',
    panel_image_path VARCHAR(512)
);

CREATE TABLE creative_jobs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    background_path VARCHAR(512) NOT NULL,
    logo_enabled BOOLEAN NOT NULL DEFAULT 1,
    logo_upload_path VARCHAR(512),
    logo_file_ids_json TEXT,
    extra_assets_enabled BOOLEAN NOT NULL DEFAULT 0,
    dealership_ids_json TEXT NOT NULL,
    formats_json TEXT NOT NULL,
    headline VARCHAR(512),
    body TEXT,
    promo_word VARCHAR(32),
    price_display VARCHAR(48),
    accent_hex VARCHAR(16),
    creative_template VARCHAR(24) NOT NULL DEFAULT 'promo_split',
    ai_generate_background BOOLEAN NOT NULL DEFAULT 0,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    warning_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE creative_outputs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES creative_jobs(id) ON DELETE CASCADE,
    dealership_id INTEGER NOT NULL REFERENCES dealerships(id),
    format_key VARCHAR(32) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    dealership_name VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE INDEX ix_dealerships_account_id ON dealerships (account_id);
CREATE INDEX ix_creative_jobs_user_id ON creative_jobs (user_id);
CREATE INDEX ix_creative_jobs_status ON creative_jobs (status);
CREATE INDEX ix_creative_outputs_job_id ON creative_outputs (job_id);

-- Default admin (password: admin123)
INSERT INTO users (id, email, hashed_password, is_active) VALUES
(1, 'admin@example.com', '$2b$12$kgBGSDNLVeVQXY7T47dPQ.wCMkTX5ffQ83evarH.Twl.Ykbt/DlHO', 1);

INSERT INTO accounts (id, name, slug, logo_path) VALUES
(1, 'Volkswagen', 'volkswagen', NULL),
(2, 'Tata', 'tata', NULL),
(3, 'Kia', 'kia', NULL),
(4, 'Hyundai', 'hyundai', NULL),
(5, 'Toyota', 'toyota', NULL),
(6, 'Honda', 'honda', NULL),
(7, 'Maruti Suzuki', 'maruti-suzuki', NULL),
(8, 'Mahindra', 'mahindra', NULL),
(9, 'Skoda', 'skoda', NULL),
(10, 'Mercedes-Benz', 'mercedes-benz', NULL);

INSERT INTO dealerships (id, account_id, code, name, address_line, phone, website, panel_image_path) VALUES
(1, 1, 'VW-Apple', 'VW-Apple', '123 Auto Row, Mumbai', '+91 22 4000 1001', 'https://vw-apple.example.com', '../assets/Dealership-panels/VW-dealers/VW-Autobhan/template.png'),
(2, 1, 'VW-KUN', 'VW-KUN', '45 Ring Road, Delhi', '+91 11 4000 1002', 'https://vw-kun.example.com', NULL),
(3, 1, 'VW-Lally', 'VW-Lally', '9 MG Road, Bengaluru', '+91 80 4000 1003', 'https://vw-lally.example.com', NULL),
(4, 1, 'VW-Motor', 'VW-Motor', '2 NH Bypass, Kochi', '+91 48 4000 1004', 'https://vw-motor.example.com', NULL),
(5, 1, 'VW-City', 'VW-City', '88 Sector 18, Noida', '+91 120 4000 1005', 'https://vw-city.example.com', NULL),
(6, 1, 'VW-Ridge', 'VW Ridge Motors', 'Baner Road, Pune', '+91 20 4000 1006', 'https://vw-ridge.example.com', NULL),
(7, 1, 'VW-Pulse', 'VW Pulse Arena', 'Salt Lake, Kolkata', '+91 33 4000 1007', 'https://vw-pulse.example.com', NULL),
(8, 2, 'TATA-North', 'Tata North Hub', 'Plot 1, Gurugram', '+91 124 5000 2001', 'https://tata-north.example.com', '../assets/Dealership-panels/Tata-dealers/Bellad-tata/template.png'),
(9, 2, 'TATA-South', 'Tata South Hub', 'OMR, Chennai', '+91 44 5000 2002', 'https://tata-south.example.com', NULL),
(10, 2, 'TATA-East', 'Tata East Plaza', 'Salt Lake, Kolkata', '+91 33 5000 2003', 'https://tata-east.example.com', NULL),
(11, 2, 'TATA-West', 'Tata West Select', 'Baner, Pune', '+91 20 5000 2004', 'https://tata-west.example.com', NULL),
(12, 2, 'TATA-Central', 'Tata Central One', 'MG Road, Hyderabad', '+91 40 5000 2005', 'https://tata-central.example.com', NULL),
(13, 3, 'KIA-Metro', 'Kia Metro', 'Ring Road, Pune', '+91 20 6000 3001', 'https://kia-metro.example.com', NULL),
(14, 3, 'KIA-Lakeside', 'Kia Lakeside', 'Lake View, Hyderabad', '+91 40 6000 3002', 'https://kia-lakeside.example.com', NULL),
(15, 3, 'KIA-Sky', 'Kia Skyline', 'Sector 18, Noida', '+91 120 6000 3003', 'https://kia-sky.example.com', NULL),
(16, 3, 'KIA-River', 'Kia Riverfront', 'Panjim, Goa', '+91 832 6000 3004', 'https://kia-river.example.com', NULL),
(17, 3, 'KIA-Urban', 'Kia Urban Drive', 'Indiranagar, Bengaluru', '+91 80 6000 3005', 'https://kia-urban.example.com', NULL),
(18, 4, 'HYU-Central', 'Hyundai Central', 'FC Road, Pune', '+91 20 6100 4101', 'https://hyu-central.example.com', NULL),
(19, 4, 'HYU-Bay', 'Hyundai Bay', 'Marine Drive, Kochi', '+91 48 6100 4102', 'https://hyu-bay.example.com', NULL),
(20, 4, 'HYU-Sky', 'Hyundai Sky Tower', 'Connaught Place, Delhi', '+91 11 6100 4103', 'https://hyu-sky.example.com', NULL),
(21, 4, 'HYU-Nova', 'Hyundai Nova', 'Vijayawada', '+91 866 6100 4104', 'https://hyu-nova.example.com', NULL),
(22, 4, 'HYU-Prime', 'Hyundai Prime Motoring', 'Jaipur', '+91 141 6100 4105', 'https://hyu-prime.example.com', NULL),
(23, 5, 'TOY-Platinum', 'Toyota Platinum', 'Sector 62, Noida', '+91 120 6200 5101', 'https://toy-platinum.example.com', NULL),
(24, 5, 'TOY-Garden', 'Toyota Garden City', 'Indiranagar, Bengaluru', '+91 80 6200 5102', 'https://toy-garden.example.com', NULL),
(25, 5, 'TOY-Crown', 'Toyota Crown Motors', 'Banjara Hills, Hyderabad', '+91 40 6200 5103', 'https://toy-crown.example.com', NULL),
(26, 5, 'TOY-Harbor', 'Toyota Harbor', 'Marine Lines, Mumbai', '+91 22 6200 5104', 'https://toy-harbor.example.com', NULL),
(27, 5, 'TOY-Highland', 'Toyota Highland', 'Dehradun', '+91 135 6200 5105', 'https://toy-highland.example.com', NULL),
(28, 6, 'HON-Civic', 'Honda Civic Motors', 'Link Road, Mumbai', '+91 22 6300 6101', 'https://hon-civic.example.com', NULL),
(29, 6, 'HON-Ridge', 'Honda Ridge', 'Salt Lake, Kolkata', '+91 33 6300 6102', 'https://hon-ridge.example.com', NULL),
(30, 6, 'HON-Prime', 'Honda Prime', 'Sitapura, Jaipur', '+91 141 6300 6103', 'https://hon-prime.example.com', NULL),
(31, 6, 'HON-Edge', 'Honda Edge', 'Guwahati', '+91 361 6300 6104', 'https://hon-edge.example.com', NULL),
(32, 6, 'HON-Metro', 'Honda Metro Lane', 'Lucknow', '+91 522 6300 6105', 'https://hon-metro.example.com', NULL),
(33, 7, 'MS-Arena', 'Maruti Arena Hub', 'Vaishali, Ghaziabad', '+91 120 6400 7101', 'https://ms-arena.example.com', NULL),
(34, 7, 'MS-Nexa', 'Nexa Select', 'Jubilee Hills, Hyderabad', '+91 40 6400 7102', 'https://ms-nexa.example.com', NULL),
(35, 7, 'MS-True', 'Maruti True Value Plus', 'Chandigarh', '+91 172 6400 7103', 'https://ms-true.example.com', NULL),
(36, 7, 'MS-Drive', 'Maruti Drive Inn', 'Nashik', '+91 253 6400 7104', 'https://ms-drive.example.com', NULL),
(37, 7, 'MS-Highway', 'Maruti Highway Motors', 'Surat', '+91 261 6400 7105', 'https://ms-highway.example.com', NULL),
(38, 8, 'MAH-Rise', 'Mahindra Rise', 'Sitapura, Jaipur', '+91 141 6500 8101', 'https://mah-rise.example.com', NULL),
(39, 8, 'MAH-Peak', 'Mahindra Peak', 'Vijayawada', '+91 866 6500 8102', 'https://mah-peak.example.com', NULL),
(40, 8, 'MAH-Forge', 'Mahindra Forge', 'Coimbatore', '+91 422 6500 8103', 'https://mah-forge.example.com', NULL),
(41, 8, 'MAH-Trail', 'Mahindra Trailhead', 'Nagpur', '+91 712 6500 8104', 'https://mah-trail.example.com', NULL),
(42, 8, 'MAH-Wave', 'Mahindra Wave', 'Visakhapatnam', '+91 891 6500 8105', 'https://mah-wave.example.com', NULL),
(43, 9, 'SKO-Vertex', 'Škoda Vertex', 'Saket, New Delhi', '+91 11 6600 9101', 'https://sko-vertex.example.com', NULL),
(44, 9, 'SKO-Apex', 'Škoda Apex', 'Baner, Pune', '+91 20 6600 9102', 'https://sko-apex.example.com', NULL),
(45, 9, 'SKO-Crystal', 'Škoda Crystal', 'Ahmedabad', '+91 79 6600 9103', 'https://sko-crystal.example.com', NULL),
(46, 9, 'SKO-Motion', 'Škoda Motion', 'Mysuru', '+91 821 6600 9104', 'https://sko-motion.example.com', NULL),
(47, 9, 'SKO-Edge', 'Škoda Edge', 'Thiruvananthapuram', '+91 471 6600 9105', 'https://sko-edge.example.com', NULL),
(48, 10, 'MB-Star', 'Mercedes-Benz Star', 'Bandra Kurla Complex, Mumbai', '+91 22 6700 1101', 'https://mb-star.example.com', NULL),
(49, 10, 'MB-Luxe', 'Mercedes-Benz Luxe', 'UB City, Bengaluru', '+91 80 6700 1102', 'https://mb-luxe.example.com', NULL),
(50, 10, 'MB-Urban', 'Mercedes-Benz Urban', 'Cyber City, Gurugram', '+91 124 6700 1103', 'https://mb-urban.example.com', NULL),
(51, 10, 'MB-Signature', 'Mercedes-Benz Signature', 'Kochi', '+91 48 6700 1104', 'https://mb-signature.example.com', NULL),
(52, 10, 'MB-One', 'Mercedes-Benz One', 'Chandigarh', '+91 172 6700 1105', 'https://mb-one.example.com', NULL);
