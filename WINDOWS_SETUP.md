# 🟦 Windows Setup Guide (Beginner Friendly)

This guide is for anyone who has never used Python before and wants to run the **Flent Lens** project on a Windows laptop. We will go step-by-step from zero to a running dashboard.

---

## Step 1: Install Python (The Engine)

Python is the "engine" that runs the code. 

1.  **Download:** Go to [python.org/downloads](https://www.python.org/downloads/) and click the big yellow **Download Python 3.xx** button.
2.  **Open the Installer:** Double-click the file you just downloaded.
3.  **🛑 CRITICAL STEP:** Before you click "Install Now", you **MUST** check the box at the bottom that says:
    > **[x] Add Python to PATH**
    *(If you skip this, the rest of the guide will not work!)*
4.  **Install:** Click **Install Now**. Once it’s finished, click **Close**.

---

## Step 2: Open the Project Folder

1.  Find the folder containing the Flent Lens code (the one you downloaded from GitHub).
2.  Go **inside** the folder so you can see files like `app.py`, `main.py`, and `requirements.txt`.
3.  **The Secret Shortcut:**
    - Look at the top of the folder window (where it shows the folder name). 
    - **Click on the blank space in the text bar** at the very top (the address bar).
    - The text will turn blue. Delete it all and just type **`cmd`** then hit **Enter**.
    - A black window will pop up. This is your "Command Center."

    *Alternative (Windows 11):* **Right-Click** in the empty white space and select **"Open in Terminal"**. 
    *Alternative (Windows 10):* Hold **Shift** and **Right-Click** then select **"Open PowerShell window here"**.

---

## Step 3: Create a "Safe Space" (Virtual Environment)

We want to create a small "walled garden" for this project so it doesn't mess up your computer.

1.  In the Command Center window, copy and paste this text and hit **Enter**:
    ```powershell
    python -m venv venv
    ```
    *(Wait about 10 seconds for it to finish.)*

2.  Now, we need to "Activate" it. Copy and paste this and hit **Enter**:
    ```powershell
    .\venv\Scripts\activate
    ```
    - **How do I know it worked?** You should see `(venv)` appear at the very beginning of the line where you type.

---

## Step 4: Install the Project Tools

Now we need to install the specific tools (like Pandas and Streamlit) that Flent Lens uses.

1.  Copy and paste this command and hit **Enter**:
    ```powershell
    pip install -r requirements.txt
    ```
    - **Note:** You will see a lot of text scrolling by. This is normal! It might take 2-5 minutes. Wait until it stops and you see the typing cursor again.

---

## Step 5: Launch the Dashboard!

This is the fun part. Let's start the visual dashboard.

1.  Copy and paste this command and hit **Enter**:
    ```powershell
    streamlit run app.py
    ```
2.  **Wait a few seconds.** Your default web browser (Chrome or Edge) should automatically open a new tab with the **Flent Lens Dashboard**.
3.  If it doesn't open automatically, look at the text in the Command Center. You will see a link like `http://localhost:8501`. Copy that and paste it into your browser.

---

## 🛠️ Common Problems (Don't Panic!)

### "Python is not recognized as an internal or external command"
- **Reason:** You forgot to check the **"Add Python to PATH"** box in Step 1.
- **Fix:** Run the Python installer again, choose "Uninstall," then run it one more time and make sure that box is checked.

### "Running scripts is disabled on this system"
- **Reason:** Windows sometimes blocks the "Activate" command for security.
- **Fix:** If Step 3 fails, copy and paste this command first, hit Enter, then try Step 3 again:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```

### How do I stop the program?
- To close the dashboard, go back to the Command Center window and press **Ctrl + C** on your keyboard. Then you can close the window.

---

*Flent Lens 2.0 · Real Estate Intelligence Platform*
