# HF Deluxe Pro Manager 🏍️

**HF Deluxe Pro Manager** is a modular Python desktop application designed as a personal motorcycle management and touring companion for the **Hero HF Deluxe Pro** (and multi-vehicle fleets).

It combines motorcycle ownership tracking, full-to-full fuel efficiency computation, scheduled maintenance reminders, replacement parts intervals, aftermarket upgrade records, financial analytics with embedded Matplotlib visualizations, and an interactive OpenStreetMap road-trip planner with OSRM routing.

---

## 1. Key Features

### 🏍️ 1. Vehicle Management
- Pre-configured for the **Hero HF Deluxe Pro** (97.2cc, 4-stroke single cylinder, xSens FI technology).
- Manage multiple motorcycles in a single application with one-click default switching.
- Tracks purchase details, registration number, engine capacity, fuel type, current odometer, and ownership cost summary.

### ⛽ 2. Fuel & Mileage Management
- **Full-to-Full Mileage Engine**: Accurate fuel efficiency calculated between consecutive full-tank refills:
  $$\text{Mileage} = \frac{\text{Distance between consecutive full refills}}{\text{Total litres consumed between refills}}$$
- **Partial Refill Accumulation**: Partial refuels are preserved and accumulated towards the subsequent full-tank refill without erroneous intermediate calculations.
- **Aggregate Statistics**: Lifetime average mileage, latest recorded mileage, best/lowest mileage, total litres, total fuel spend, average fuel price, and refuel count.
- Chronological validation preventing negative values and invalid odometer progression.

### 🔧 3. Maintenance & Servicing
- Complete workshop logging: service dates, odometer readings, service categories, descriptions, labour charges, parts charges, and mechanic details.
- **Replacement Parts Tracking**: Add multiple parts per service with unit price, quantities, and configurable replacement intervals (kilometres and months).
- **Maintenance Reminders**: Automatic status evaluation (Overdue, Due Soon, Good) based on current odometer readings and elapsed calendar time.

### ✨ 4. Aftermarket Parts & Upgrades
- Dedicated system for accessories and modifications (Lighting, Luggage, Seats, Mirrors, Performance, Crash protection).
- Kept strictly separate from routine maintenance expenses to maintain clean financial analytics.
- Chronological modification log and total upgrade investment tracking.

### 📈 5. Financial Analytics & Visualizations
- Interactive Matplotlib visualizations embedded directly into Tkinter:
  1. **Expense Distribution Donut Chart** (Fuel vs. Maintenance vs. Upgrades vs. Misc)
  2. **Monthly Expenditure Stacked Bar Chart**
  3. **Fuel Efficiency Trend Line Graph** (km/l over time)
  4. **Petrol Price History Trend** (₹/L over time)
  5. **Cumulative Distance Progression Graph**
- Metrics: Total ownership expenditure, total operational cost, running cost per kilometre, and average monthly spend.

### 🗺️ 6. Interactive Tour Planner & Multi-Stage Routing
- **TkinterMapView** integration with OpenStreetMap tiles.
- **Nominatim Geocoding & Reverse Geocoding** with caching and rate limiting.
- **OSRM Routing Engine**: Computes road distance, travel duration, and route geometry.
- **Multi-Stop Journeys**: Add, remove, and reorder intermediate tour stops (e.g., *Chennai → Mahabalipuram → Pondicherry → Chidambaram*).
- **Fuel Budget Estimator**: Computes expected fuel consumption (L), one-way and return trip expenditures, and cost per kilometre based on the motorcycle's recorded average mileage or manual override.
- **Offline Haversine Fallback**: Estimates road distances if internet connectivity is unavailable.

### 🏁 7. Trip History & Actual Expenditure Analysis
- Saved trip status management: *Planned*, *Completed*, *Cancelled*.
- Trip completion dialog capturing actual odometer readings, actual fuel consumed, toll, parking, and additional tour costs.
- **Estimated vs Actual Variance Analysis**: Detailed comparison between expected and actual distance, fuel, costs, and cost per kilometre.
- **PDF Export**: Generate PDF trip summaries and itineraries using ReportLab.

### ⚙️ 8. Settings & Database Management
- Live SQLite database backup and restore using SQLite's online backup API.
- Configurable default fuel efficiency, petrol price, currency symbol, distance units, and API endpoints.

---

## 2. Technology Stack

- **Language**: Python 3.12+
- **GUI Framework**: Tkinter & `ttk` (Modern Dark Theme)
- **Database**: SQLite3 with foreign key enforcement and indexed queries
- **Data Visualizations**: Matplotlib (with `FigureCanvasTkAgg`)
- **Map & Geodata**: `tkintermapview`, OpenStreetMap tiles
- **APIs**: Nominatim (OSM Geocoding), OSRM (Road Routing)
- **PDF Generation**: ReportLab
- **Testing**: Python standard `unittest` and `pytest`

---

## 3. Project Directory Architecture

```
APPClasses/
├── main.py                     # Application entry point and navigation controller
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation and usage guide
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # Central SQLite manager, backup, restore, transactions
│   └── schema.sql              # Relational database schema with 10 tables and indexes
│
├── models/
│   ├── __init__.py
│   ├── vehicle.py              # Vehicle dataclass and CRUD repository
│   ├── fuel.py                 # Refuel dataclass, repository, and auto-mileage runner
│   ├── maintenance.py          # Service and Part dataclasses and repository
│   ├── upgrades.py             # Upgrade dataclass and repository
│   ├── expense.py              # Miscellaneous expense dataclass and repository
│   ├── trips.py                # Trip, Waypoint, SavedLocation models and repository
│   └── settings.py             # Persistent application preferences repository
│
├── services/
│   ├── __init__.py
│   ├── fuel_calculator.py      # Full-to-full mileage engine and partial refill accumulator
│   ├── maintenance_calculator.py# Service totals and upcoming/overdue reminder evaluator
│   ├── expense_calculator.py   # Financial breakdown and cost per kilometre calculator
│   └── trip_calculator.py      # Fuel consumption estimator and actual vs estimated variance
│
├── api/
│   ├── __init__.py
│   ├── geocoding.py            # Nominatim client with rate-limiting and cache
│   └── routing.py              # OSRM router with async background worker and Haversine fallback
│
├── ui/
│   ├── __init__.py
│   ├── styles.py               # Dark/Light theme colors, typography, and ttk styles
│   ├── components.py           # StatCard, ScrollableFrame, DataTable, ToastNotification
│   ├── dashboard.py            # Overview dashboard with key metrics and quick actions
│   ├── vehicle.py              # Vehicle profile and fleet management page
│   ├── fuel.py                 # Refuelling logs, full-tank indicator, and fuel statistics
│   ├── maintenance.py          # Service records, parts intervals, and reminder alerts
│   ├── upgrades.py             # Aftermarket modifications and chronology page
│   ├── analytics.py            # Financial dashboard with embedded Matplotlib charts
│   ├── trip_planner.py         # TkinterMapView interactive map and route planner
│   ├── trip_history.py         # Saved trips, completion analysis, and PDF export
│   └── settings.py             # App preferences, backup/restore, and attribution
│
├── visualizations/
│   ├── __init__.py
│   ├── expense_charts.py       # Donut and stacked bar charts
│   └── fuel_charts.py          # Mileage trend, price trend, and distance graphs
│
├── data/
│   └── motorcycle.db           # Persistent SQLite database file
│
└── tests/
    ├── test_phase1.py          # Phase 1 foundation and initial logic tests
    ├── test_core_calculations.py# Calculation engines, validations, and mocked API tests
    └── test_gui_integration.py  # GUI window creation and navigation across all 9 pages
```

---

## 4. Installation and Setup

### Prerequisites
- Windows 10/11
- Python 3.10+ (Python 3.12 recommended)

### 1. Set Up Virtual Environment
```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 5. Running the Application

Launch the desktop application via `main.py`:

```powershell
.\.venv\Scripts\python.exe main.py
```

The application will start in dark mode, initialize `data/motorcycle.db`, and display the Dashboard with your pre-configured **Hero HF Deluxe Pro**.

---

## 6. Running the Automated Tests

All core calculations and database routines run independently of network access and the GUI thread.

Run the entire test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

To run individual test modules:
```powershell
# Core calculations, mileage engine, partial refills, and mocked APIs:
.\.venv\Scripts\python.exe -m unittest tests/test_core_calculations.py

# GUI page navigation and component integration:
.\.venv\Scripts\python.exe -m unittest tests/test_gui_integration.py
```

---

## 7. License & Attribution

- Built as a native desktop application in Python.
- Map data © [OpenStreetMap](https://www.openstreetmap.org/) contributors under the Open Database License (ODbL).
- Routing engine powered by [OSRM](http://project-osrm.org/).
- Geocoding powered by [Nominatim](https://nominatim.org/).

