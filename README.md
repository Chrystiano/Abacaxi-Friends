# 🎉 Event Attendance Management - Streamlit App

## 📌 Overview
This **Event Attendance Management** system is a modern **Streamlit-based web application** designed to streamline the process of managing event registrations, confirming payments, and ensuring a seamless user experience. The system provides a beautiful, responsive, and **Apple-inspired UX/UI design**, built using the latest best practices for **Python 3.11** and **Streamlit Community Cloud** deployment.

The application enables users to:
- 📌 **Search and confirm their attendance** by uploading a proof of payment.
- 📝 **Register new attendees** while preventing duplicate entries.
- 🔄 **Automatically update a CSV file** to maintain a structured database.
- 🚀 **Run entirely in the cloud using Streamlit Community Cloud** for easy access.

This application ensures **data integrity, simplicity, and efficiency**, making event management effortless and user-friendly.

---

## ⚡ Features
### ✅ Attendance Confirmation
- Users can **search for their name** in the system.
- If a record is found, they are prompted to upload a **payment confirmation document**.
- The system supports **CSV, PNG, JPG, and PDF formats (max 2MB per file)**.
- **Files are stored with a timestamped name** for organization.
- Once uploaded, the system **automatically updates the CSV file**, marking the user as "Payment Confirmed".

### 📝 New Attendee Registration
- The system allows **new users to register for the event**.
- **Duplicate registrations are not allowed**, ensuring data consistency.
- All new registrations are **automatically assigned the type 'Novo'**.
- Registrations are **immediately saved to the CSV file**.

### 🛠️ Streamlit-Powered UI
- **Elegant and modern UI**, inspired by **Apple's Human Interface Guidelines**.
- Fully **responsive**, adapting seamlessly to desktops, tablets, and mobile devices.
- **Instant feedback and notifications** to guide the user.
- Animated effects such as **balloons on successful confirmation** for enhanced UX.

---

## 📂 File Structure
```
📁 EventAttendanceApp/
│── 📜 app.py            # Main Streamlit app
│── 📜 registros.csv      # CSV database (auto-updated)
│── 📁 uploads/          # Folder where uploaded files are stored
│── 📜 README.md         # This documentation file
│── 📜 requirements.txt  # Python dependencies
```

---

## 🚀 Installation & Usage

### 1️⃣ **Clone the repository**
```bash
git clone https://github.com/yourusername/EventAttendanceApp.git
cd EventAttendanceApp
```

### 2️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3️⃣ **Run the Application**
```bash
streamlit run app.py
```

🔗 Open [http://localhost:8501](http://localhost:8501) in your browser to use the app.

---

## 🌍 Deployment on Streamlit Community Cloud
To deploy this app to **Streamlit Community Cloud**, follow these steps:
1. **Create a repository on GitHub** and push your project files.
2. Go to **[Streamlit Community Cloud](https://share.streamlit.io)**.
3. Click **New App** and connect your GitHub repo.
4. Select `app.py` as the entry point and click **Deploy**.
5. 🎉 Your app is now live!

---

## 🔄 How the System Works

### 1️⃣ **Attendance Confirmation Process**
✔ User searches for their name.
✔ If found, they select their record and upload a proof of payment.
✔ File is **saved with a timestamped name** inside `/uploads`.
✔ CSV file is updated, changing status to **'Pagamento Confirmado'**.
✔ Success message and **animated balloons** appear to confirm completion.

### 2️⃣ **New Attendee Registration**
✔ User enters **name and phone number**.
✔ The system ensures that **no duplicate names exist**.
✔ The **new attendee is assigned the type 'Novo'** automatically.
✔ Data is saved directly to the **CSV file**.
✔ A success message confirms the registration.

---

## ⚙️ Technologies Used
- **Python 3.11** 🐍
- **Streamlit 1.41.1** 🖥️
- **Pandas** for data handling 📊
- **Watchdog** for file updates 🔄

---

## 📜 License
This project is licensed under the **MIT License**. Feel free to use, modify, and distribute it.

---

## 🤝 Contributing
We welcome contributions! To contribute:
1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature-name`)
3. **Commit changes** (`git commit -m 'Add new feature'`)
4. **Push the branch** (`git push origin feature-name`)
5. **Open a Pull Request** 🚀

---

## 📧 Contact
For support, reach out via:
🐙 GitHub: [Chrystiano](https://github.com/Chrystiano)

---

🎉 **Enjoy using the Event Attendance Management System!** 🚀
