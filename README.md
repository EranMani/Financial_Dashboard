# Project: Local Finance Dashboard
## Lesson: Building Privacy-First Data Apps with NiceGUI

### 📄 Overview
We move away from cloud-based aggregators to build a **Local-First** financial dashboard. This project demonstrates how to ingest raw banking data (CSV/Excel), sanitize messy Hebrew encodings, and visualize cash flow using Python—all without sending a single byte of sensitive financial data to the internet.

### 🛠️ The Tech Stack (The "Modern Data App")

| Component | Library | Role | Engineering Note |
| :--- | :--- | :--- | :--- |
| **Frontend** | NiceGUI | User Interface | A wrapper around Vue.js that lets you write modern, reactive web UIs in pure Python. |
| **Data Core** | Pandas | ETL Engine | The "Assembly Line." Ingests, cleans, and merges disparate bank files into a uniform DataFrame. |
| **Visuals** | ECharts | Analytics | High-performance interactive charts (Pie & Bar) embedded directly via NiceGUI. |
| **Manager** | uv | Dependency | Replaces `pip` for lightning-fast environment creation and management. |

### ⚙️ The Architecture: "The Factory Line"

#### 1. The Normalization Layer (`data_loader.py`)
* **The Problem:** Banks and Credit Cards output garbage data. We deal with inconsistent encodings (`utf-8` vs `cp1255`), varying column names ("Debit" vs "Chova"), and mixed file formats (XLSX vs CSV).
* **The Fix:** We build a universal adapter that "sniffs" the file structure, handles Hebrew encoding issues automatically, and outputs a single, clean DataFrame.

#### 2. The Rule Book (`config.py`)
* **Concept:** Hardcoding strings inside logic code is a "Junior" mistake.
* **The Strategy:** We externalize all business logic.
    * **Categorization:** Keyword lists (e.g., "Shufersal" -> "Groceries") live here.
    * **Styling:** Hex codes for graphs and UI themes.
* **Benefit:** To add a new category, you edit the config, not the engine.

#### 3. The Reactive Dashboard (`main.py`)
* **The "Senior" Approach:** The UI is purely Reactive. It does not store state; it reflects the state of the Engine.
* **Drill-Down:** Clicking a slice of the Pie Chart triggers a callback to filter the AG Grid transaction table.
* **Responsive:** Layouts adapt intelligently from Grid (Desktop) to Column (Mobile).

### 🚀 Usage Guide: "One-Click Deploy"

| Step | Action | Description |
| :--- | :--- | :--- |
| **1. Generate Data** | `python create_demo_files.py` | *(Optional)* If you don't have real bank files, this script creates a `/demo_data` folder with Hebrew filenames and randomized transactions. |
| **2. Launch App** | Double-click `run_app.bat` | **Auto-Magic:** Checks for Python, installs `uv`, creates a `.venv`, installs dependencies from `requirements.txt`, and launches the browser. |

### 🧠 Strategic Takeaway
**"Separation of Concerns."**
Notice how the files are split based on responsibility, not just size:
* `config.py` contains **Rules**.
* `data_loader.py` contains **Processing**.
* `main.py` contains **Presentation**.

If the bank changes their CSV format, you fix the loader. If you want to change the color scheme, you fix the config. **Never mix your business logic with your pixel-pushing logic.**
