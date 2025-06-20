# Doctor Appointment Booking System

A comprehensive appointment booking system built with FastAPI, Streamlit, and SQLite, containerized with Docker.

## 🏗️ Architecture

- **Frontend**: Streamlit (Python) - Port 8501
- **Backend**: FastAPI - Port 8000  
- **Database**: SQLite (containerized)
- **Architecture**: Microservices (ready for ML integration)

## 📋 Features

### For Doctors
- Set and manage weekly schedules
- View appointments (filtered by date)
- Update appointment status (scheduled → completed)
- Prevent schedule changes that conflict with existing appointments

### For Patients  
- Browse available doctors
- View real-time available time slots
- Book appointments with reasons
- View and cancel appointments
- Visual calendar interface

### Security
- Session-based authentication
- Password hashing (bcrypt)
- Role-based access control
- CSRF protection

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd doctor-appointment-system
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Build and run containers**
```bash
docker-compose up --build
```

4. **Access the application**
- Frontend: http://localhost:8501
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
doctor-appointment-system/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   └── security.py
│       ├── api/
│       │   └── v1/
│       │       ├── auth.py
│       │       ├── users.py
│       │       ├── appointments.py
│       │       ├── schedules.py
│       │       └── dependencies.py
│       ├── models/
│       │   └── models.py
│       ├── schemas/
│       │   └── schemas.py
│       └── crud/
│           ├── crud_user.py
│           ├── crud_appointment.py
│           └── crud_schedule.py
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── database/
    ├── Dockerfile
    └── init.sql
```

## 🧪 Testing Instructions

### Step 1: Register Users

1. **Register a Doctor**
   - Go to http://localhost:8501
   - Click "Register" tab
   - Fill in:
     - Username: `dr_smith`
     - Email: `dr.smith@example.com`
     - Full Name: `Dr. John Smith`
     - Password: `password123`
     - Role: `doctor`
   - Click Register

2. **Register a Patient**
   - Fill in:
     - Username: `john_patient`
     - Email: `john@example.com`
     - Full Name: `John Doe`
     - Password: `password123`
     - Role: `patient`
   - Click Register

### Step 2: Doctor Setup

1. **Login as Doctor**
   - Username: `dr_smith`
   - Password: `password123`

2. **Set Schedule**
   - Go to "Schedule Management" tab
   - Click "Add New Schedule"
   - Add multiple schedules:
     - Monday: 9:00 AM - 5:00 PM, 30 min slots
     - Wednesday: 9:00 AM - 5:00 PM, 30 min slots
     - Friday: 9:00 AM - 1:00 PM, 30 min slots

### Step 3: Patient Booking

1. **Logout and Login as Patient**
   - Username: `john_patient`
   - Password: `password123`

2. **Book Appointment**
   - Go to "Book Appointment" tab
   - Select "Dr. John Smith"
   - Choose a date (must be Monday, Wednesday, or Friday)
   - Select an available time slot
   - Enter reason: "Regular checkup"
   - Click "Book Appointment"

### Step 4: Manage Appointments

1. **As Patient**
   - View appointments in "My Appointments" tab
   - Test cancellation feature

2. **As Doctor**
   - Login as doctor again
   - View appointments in "Appointments" tab
   - Filter by date
   - Mark appointments as completed

## 🐛 Troubleshooting

### Common Issues

1. **Cannot connect to backend**
   - Ensure all containers are running: `docker-compose ps`
   - Check backend logs: `docker-compose logs backend`

2. **Database errors**
   - Restart containers: `docker-compose restart`
   - Reset database: `docker-compose down -v && docker-compose up --build`

3. **Login issues**
   - Clear browser cookies
   - Check backend logs for errors

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f database
```

## 🔧 Development

### Running in Development Mode

Create `docker-compose.dev.yml`:
```yaml
version: '3.8'

services:
  backend:
    volumes:
      - ./backend/app:/app/app
    environment:
      - RELOAD=True
  
  frontend:
    volumes:
      - ./frontend:/app
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### API Testing with curl

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","full_name":"Test User","password":"test123","role":"patient"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# Get doctors
curl http://localhost:8000/api/v1/users/doctors
```

## 🏗️ ML Integration (Future)

The architecture supports easy ML module integration:

1. Add ML service to `docker-compose.yml`
2. ML service can access data via backend API
3. Frontend can display ML predictions
4. Example use cases:
   - Appointment time recommendations
   - No-show predictions
   - Optimal scheduling suggestions

## 📝 Database Schema

### Users Table
- id (Primary Key)
- username (Unique)
- email (Unique)
- full_name
- hashed_password
- role (doctor/patient)
- is_active
- created_at

### Schedules Table
- id (Primary Key)
- doctor_id (Foreign Key)
- day_of_week (0-6)
- start_time
- end_time
- slot_duration
- is_active
- created_at

### Appointments Table
- id (Primary Key)
- doctor_id (Foreign Key)
- patient_id (Foreign Key)
- appointment_date
- appointment_time
- duration
- reason
- status (scheduled/completed/cancelled)
- created_at
- updated_at

## 🔒 Security Features

- Password hashing with bcrypt
- Session-based authentication
- HTTPOnly cookies
- CORS configuration
- Input validation with Pydantic
- SQL injection protection (ORM)
- Role-based access control

## 📄 License

This project is provided as-is for educational and development purposes.