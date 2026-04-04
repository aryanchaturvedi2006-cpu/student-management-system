# EduSync Hub - Next-Gen Student Management System

![EduSync Hub](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Framework-Flask-black)

EduSync is a comprehensive, multi-role web application designed to streamline academic administration, attendance tracking, and institutional fee processing. Built entirely with **Python/Flask** and featuring a modern, responsive Glassmorphism dashboard interface.

---

## 🌟 Key Features

### 1. Robust Multi-Role Authentication
- **Admin Access**: Secure master dashboard access to manipulate global database configurations.
- **Student Access**: Dedicated read-only portals isolated by secure login (using Roll Numbers).
- **Security Check**: Industry-grade PBKDF2 mathematical password hashing powered by `Werkzeug.security`.

### 2. Academic Matrix (CRUD)
- Complete database controls to Create, Read, Update, and Delete student records.
- Dynamically add multiple courses per student and auto-calculate cumulative GPA algorithmically.

### 3. Integrated Attendance Tracking
- Admins can log daily, course-specific registers (Present/Absent).
- The dashboard automatically computes live attendance percentage thresholds per class.

### 4. Financial & Fee Subsystem
- **Admin Ledger Setup**: Assign unique course fees and due dates to specific students. Manually record cash/bank transfers.
- **Student Checkout Sandbox**: Students can view outstanding balances and securely "pay" them through an integrated checkout gateway sandbox that mirrors realistic web transaction flows.

---

## 💻 Tech Stack Specification

- **Backend Architecture**: Python 3.x, micro-framework **Flask**
- **Database Engine**: **SQLite3** (Serverless, natively initialized via backend scripts)
- **Frontend Layer**: HTML5, Vanilla JavaScript (ES6+ async `fetch()` APIs), Custom Vanilla CSS3 (Glassmorphism styling)

---

## 🚀 Getting Started locally

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You need Python 3 installed on your machine. You can download it from [python.org](https://www.python.org/downloads/).

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/student-management-system.git
   cd student-management-system
   ```

2. **Create a Virtual Environment (Optional but Recommended)**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On MacOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database and Start Server**
   ```bash
   python app.py
   ```
   > The script automatically builds `students.db` natively via `sqlite3` execution commands on launch.

5. **Access the application**
   Open your web browser and navigate to: `http://127.0.0.1:5000`

### Default System Credentials
To log in immediately after setup, use the system default administration credentials:
- **Username**: `admin`
- **Password**: `admin123`

---

## 🤝 Project Internship Purpose
This project was heavily engineered to demonstrate complex SaaS capabilities including API construction, DOM manipulation without heavyweight frontend frameworks, Relational Database schema design, and secure cryptography concepts.
