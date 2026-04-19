# ClinicOS — Setup Guide

## Quick Start (Windows)

1. **Install Python** (one time only)
   - Go to https://python.org/downloads
   - Download and install Python 3.x
   - ✅ CHECK "Add Python to PATH" during install

2. **Run the app**
   - Double-click `START_CLINICOS.bat`
   - Browser opens automatically at http://localhost:5000

3. **Login**
   - Username: `admin`
   - Password: `admin123`
   - ⚠️ Change this password after first login (Users tab)

---

## Access from Your Phone (Android/iPhone)

1. Make sure your phone is on the **same WiFi** as your PC
2. The launcher shows your PC's IP address (e.g. 192.168.1.5)
3. Open Chrome on your phone → go to `http://192.168.1.5:5000`
4. To install as an app:
   - Android: Tap the 3-dot menu → "Add to Home screen"
   - iPhone: Tap Share → "Add to Home Screen"

---

## Features

- **Dashboard** — Live stats: patients, today's visits, overdue, low stock
- **Patients** — Register with name, father's name, gender, age, phone, Aadhaar (auto-assigned patient ID 0001, 0002...)
- **Prescribe** — Assign medicines from inventory, set days, auto-calculates next visit date
- **Inventory** — Add medicines, track stock, get low-stock alerts
- **Upcoming Visits** — See all patients sorted by next visit with overdue/today/upcoming status
- **User Management** — Admin can create staff logins, remove users, change passwords

---

## User Roles

- **Admin** — Full access: all features + user management + delete medicines
- **Staff** — Clinical access: patients, prescriptions, inventory (no user management)

---

## Data Storage

All data is stored in `clinic.db` (SQLite database) in the same folder.
**Back up this file regularly** to avoid data loss.

---

## For Internet Access (Optional)

To access from anywhere (not just your clinic WiFi):
- Deploy to a free/cheap cloud server (Render.com free tier, Railway.app, etc.)
- Or use a service like ngrok for temporary remote access

Contact a developer or ask Claude for help with cloud deployment.
