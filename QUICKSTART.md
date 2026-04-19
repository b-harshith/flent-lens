# 🚀 Flent Lens — Quick Setup & Execution Guide

This guide will walk you through setting up and running the Flent Lens project on a fresh laptop that doesn't have Python installed yet.

---

## 1. Install Python

Flent Lens requires **Python 3.10 or higher**.

### 🍎 For macOS
1. Open your **Terminal** (Cmd + Space, type "Terminal").
2. Check if Python is already there (it might be): `python3 --version`.
3. If not found, download and install the latest version from [python.org](https://www.python.org/downloads/macos/).
4. **Recommended (via Homebrew):** If you have Homebrew, run:
   ```bash
   brew install python
   ```

### 🪟 For Windows
1. Download the installer from [python.org](https://www.python.org/downloads/windows/).
2. **IMPORTANT:** When running the installer, check the box that says **"Add Python to PATH"**.
3. Open **Command Prompt** or **PowerShell** and verify:
   ```cmd
   python --version
   ```

---

## 2. Set Up the Project

Once Python is installed, follow these steps in your terminal.

### Step 1: Navigate to the Project Folder
Use the `cd` command to enter the folder where you saved the code.

**Windows Tip:** If you see an "Invalid path" error, try these:
1.  **Use Quotes:** Type `cd ` (with a space) then drag and drop. If it doesn't have quotes, add them manually: `cd "C:\Path With Spaces\Folder"`.
2.  **Drive Change:** If your folder is on a different drive (e.g., `D:`), you must use the `/d` flag: `cd /d "D:\Your Folder"`.
3.  **The Easiest Way:** Instead of typing `cd`, hold **Shift** and **Right-Click** inside the project folder in File Explorer, and select **"Open PowerShell window here"** or **"Open Command window here"**. This will open the terminal already inside the correct folder.

```bash
# Example (adjust the path to where you saved it)
cd "Path/To/BBA_Python_final"
```

### Step 2: Create a Virtual Environment
This keeps the project's dependencies separate from your system.
```bash
# macOS/Linux
python3 -m venv venv

# Windows
python -m venv venv
```

### Step 3: Activate the Environment
```bash
# macOS/Linux
source venv/bin/activate

# Windows
.\venv\Scripts\activate
```
*Note: Once activated, you should see `(venv)` appearing at the start of your terminal prompt.*

---

## 3. Install Dependencies

Install all the necessary libraries (pandas, streamlit, geopandas, etc.) with one command:
```bash
pip install -r requirements.txt
```
*This may take 2-5 minutes depending on your internet speed.*

---

## 4. Run the Program

### 🔬 Option A: Run the Analysis Pipeline
Use this to regenerate the analytical reports (Excel, KML maps) for specific cities.
```bash
# Run analysis for Bangalore
python main.py --city bangalore

# Run analysis for all 15 cities
python main.py --all-cities
```

### 📊 Option B: Run the Visual Dashboard
Use this to launch the interactive browser interface.
```bash
streamlit run app.py
```
*Wait for the terminal to provide a local URL (e.g., `http://localhost:8501`). Copy and paste it into Chrome or Safari.*

---

## 🛠 Troubleshooting

*   **`python` or `python3` command not found:** Ensure Python is installed and added to your system PATH.
*   **Permissions errors on Mac:** If you get a permission error, try using `sudo` (not recommended for pip) or verify folder permissions.
*   **Geopandas installation fails:** On Windows, if `geopandas` or `fiona` fails to install, you might need to install the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

---

*Flent Lens 2.0 · Professional Market Intelligence*
