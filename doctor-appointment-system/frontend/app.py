import streamlit as st
import requests
from datetime import datetime, date, time, timedelta
import os
import uuid

# API Configuration
API_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize session storage
if 'auth_tokens' not in st.session_state:
    st.session_state.auth_tokens = {}


# Helper functions
def get_session_id():
    """Get or create a session ID from query params"""
    query_params = st.query_params

    if "session_id" not in query_params:
        # Create new session ID
        session_id = str(uuid.uuid4())
        st.query_params["session_id"] = session_id
        return session_id

    return query_params["session_id"]


def get_auth_token():
    """Get auth token for current session"""
    session_id = get_session_id()
    return st.session_state.auth_tokens.get(session_id)


def set_auth_token(token):
    """Set auth token for current session"""
    session_id = get_session_id()
    st.session_state.auth_tokens[session_id] = token


def clear_auth_token():
    """Clear auth token for current session"""
    session_id = get_session_id()
    if session_id in st.session_state.auth_tokens:
        del st.session_state.auth_tokens[session_id]
    # Also clear query params
    st.query_params.clear()


def make_request(method, endpoint, json=None, params=None):
    """Make API request with error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        cookies = {}
        token = get_auth_token()
        if token:
            cookies = {'access_token': token}

        response = requests.request(
            method=method,
            url=url,
            json=json,
            params=params,
            cookies=cookies
        )
        return response
    except requests.exceptions.ConnectionError:
        st.error("Unable to connect to the backend. Please ensure the backend is running.")
        return None


def check_existing_session():
    """Check if user has an existing valid session"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None

        # Try to validate existing token
        token = get_auth_token()
        if token:
            response = make_request("GET", "/api/v1/auth/me")
            if response and response.status_code == 200:
                # Valid session exists
                user_data = response.json()
                st.session_state.logged_in = True
                st.session_state.user = user_data
                return True
            else:
                # Invalid token, clear it
                clear_auth_token()

    return st.session_state.get('logged_in', False)


def login(username, password):
    """Login user"""
    response = make_request(
        "POST",
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )

    if response and response.status_code == 200:
        data = response.json()
        st.session_state.logged_in = True
        st.session_state.user = data["user"]
        # Store token in session state with session ID
        set_auth_token(data["access_token"])
        return True
    return False


def logout():
    """Logout user"""
    make_request("POST", "/api/v1/auth/logout")
    # Clear session state
    st.session_state.logged_in = False
    st.session_state.user = None
    # Clear auth token and session ID
    clear_auth_token()


def register(username, email, full_name, password, role):
    """Register new user"""
    response = make_request(
        "POST",
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": password,
            "role": role
        }
    )

    if response and response.status_code == 200:
        return True, "Registration successful! Please login."
    elif response:
        return False, response.json().get("detail", "Registration failed")
    else:
        return False, "Connection error"


# Main App
st.set_page_config(
    page_title="Doctor Appointment System",
    page_icon="🏥",
    layout="wide"
)

# Check for existing session on page load
check_existing_session()

# Header
st.title("🏥 Doctor Appointment System")

# Show session info in sidebar for debugging (remove in production)
with st.sidebar:
    if st.session_state.get('logged_in', False):
        st.write("Session Info:")
        st.write(f"User: {st.session_state.user['username']}")
        st.write(f"Role: {st.session_state.user['role']}")
        session_id = get_session_id()
        st.write(f"Session ID: {session_id[:8]}...")

# Authentication section
if not st.session_state.get('logged_in', False):
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if login(username, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            reg_username = st.text_input("Username")
            reg_email = st.text_input("Email")
            reg_full_name = st.text_input("Full Name")
            reg_password = st.text_input("Password", type="password")
            reg_role = st.selectbox("Role", ["patient", "doctor"])
            submit_reg = st.form_submit_button("Register")

            if submit_reg:
                success, message = register(
                    reg_username, reg_email, reg_full_name,
                    reg_password, reg_role
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

else:
    # User is logged in
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"Welcome, **{st.session_state.user['full_name']}** ({st.session_state.user['role'].title()})")
    with col3:
        if st.button("Logout"):
            logout()
            st.rerun()

    st.divider()

    # Role-based dashboard
    if st.session_state.user['role'] == 'doctor':
        # Doctor Dashboard
        st.header("Doctor Dashboard")

        tab1, tab2, tab3 = st.tabs(["Schedule Management", "Appointments", "Statistics"])

        with tab1:
            st.subheader("My Schedule")

            # Add new schedule
            with st.expander("Add New Schedule"):
                with st.form("add_schedule"):
                    col1, col2 = st.columns(2)
                    with col1:
                        day_of_week = st.selectbox(
                            "Day of Week",
                            options=list(range(7)),
                            format_func=lambda x:
                            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][x]
                        )
                        start_time = st.time_input("Start Time", time(9, 0))
                    with col2:
                        end_time = st.time_input("End Time", time(17, 0))
                        slot_duration = st.number_input("Slot Duration (minutes)", min_value=15, max_value=120,
                                                        value=30)

                    submit_schedule = st.form_submit_button("Add Schedule")

                    if submit_schedule:
                        response = make_request(
                            "POST",
                            "/api/v1/schedules/",
                            json={
                                "day_of_week": day_of_week,
                                "start_time": str(start_time),
                                "end_time": str(end_time),
                                "slot_duration": slot_duration
                            }
                        )

                        if response and response.status_code == 200:
                            st.success("Schedule added successfully!")
                            st.rerun()
                        elif response:
                            st.error(response.json().get("detail", "Failed to add schedule"))

            # Display schedules
            response = make_request("GET", "/api/v1/schedules/my")
            if response and response.status_code == 200:
                schedules = response.json()
                if schedules:
                    for schedule in schedules:
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
                            schedule['day_of_week']]
                        with col1:
                            st.write(f"**{day_name}**")
                        with col2:
                            st.write(f"{schedule['start_time']} - {schedule['end_time']}")
                        with col3:
                            st.write(f"{schedule['slot_duration']} min slots")
                        with col4:
                            if st.button("Delete", key=f"del_{schedule['id']}"):
                                del_response = make_request("DELETE", f"/api/v1/schedules/{schedule['id']}")
                                if del_response and del_response.status_code == 200:
                                    st.success("Schedule deleted")
                                    st.rerun()
                                elif del_response:
                                    st.error(del_response.json().get("detail", "Cannot delete"))
                else:
                    st.info("No schedules set. Please add your availability.")

        with tab2:
            st.subheader("My Appointments")

            # Filter appointments
            filter_date = st.date_input("Filter by date", value=date.today())

            response = make_request("GET", "/api/v1/appointments/my")
            if response and response.status_code == 200:
                appointments = response.json()

                # Filter by date if requested
                filtered_appointments = [
                    apt for apt in appointments
                    if apt['appointment_date'] == str(filter_date)
                ] if filter_date else appointments

                if filtered_appointments:
                    for apt in filtered_appointments:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                            with col1:
                                st.write(f"**{apt['patient']['full_name']}**")
                                st.write(f"Date: {apt['appointment_date']}")
                            with col2:
                                st.write(f"Time: {apt['appointment_time']}")
                                st.write(f"Status: {apt['status']}")
                            with col3:
                                st.write(f"Reason: {apt['reason']}")
                            with col4:
                                if apt['status'] == 'scheduled':
                                    if st.button("Complete", key=f"comp_{apt['id']}"):
                                        update_response = make_request(
                                            "PUT",
                                            f"/api/v1/appointments/{apt['id']}",
                                            json={"status": "completed"}
                                        )
                                        if update_response and update_response.status_code == 200:
                                            st.success("Marked as completed")
                                            st.rerun()
                            st.divider()
                else:
                    st.info("No appointments for the selected date.")

        with tab3:
            st.subheader("Statistics")
            response = make_request("GET", "/api/v1/appointments/my")
            if response and response.status_code == 200:
                appointments = response.json()

                col1, col2, col3 = st.columns(3)
                with col1:
                    total = len(appointments)
                    st.metric("Total Appointments", total)
                with col2:
                    scheduled = len([a for a in appointments if a['status'] == 'scheduled'])
                    st.metric("Scheduled", scheduled)
                with col3:
                    completed = len([a for a in appointments if a['status'] == 'completed'])
                    st.metric("Completed", completed)

    else:
        # Patient Dashboard
        st.header("Patient Dashboard")

        tab1, tab2 = st.tabs(["Book Appointment", "My Appointments"])

        with tab1:
            st.subheader("Book New Appointment")

            # Get list of doctors
            response = make_request("GET", "/api/v1/users/doctors")
            if response and response.status_code == 200:
                doctors = response.json()

                if doctors:
                    selected_doctor = st.selectbox(
                        "Select Doctor",
                        options=doctors,
                        format_func=lambda x: f"Dr. {x['full_name']}"
                    )

                    if selected_doctor:
                        col1, col2 = st.columns(2)
                        with col1:
                            appointment_date = st.date_input(
                                "Select Date",
                                min_value=date.today(),
                                max_value=date.today() + timedelta(days=30)
                            )

                        # Get available slots
                        if appointment_date:
                            slots_response = make_request(
                                "GET",
                                f"/api/v1/schedules/doctor/{selected_doctor['id']}/available-slots",
                                params={
                                    "start_date": str(appointment_date),
                                    "end_date": str(appointment_date)
                                }
                            )

                            if slots_response and slots_response.status_code == 200:
                                available_slots = slots_response.json()

                                if available_slots:
                                    with col2:
                                        time_options = [slot['time'] for slot in available_slots]
                                        selected_time = st.selectbox("Select Time", options=time_options)

                                    reason = st.text_area("Reason for appointment")

                                    if st.button("Book Appointment"):
                                        if reason:
                                            booking_response = make_request(
                                                "POST",
                                                "/api/v1/appointments/",
                                                json={
                                                    "doctor_id": selected_doctor['id'],
                                                    "appointment_date": str(appointment_date),
                                                    "appointment_time": selected_time,
                                                    "reason": reason
                                                }
                                            )

                                            if booking_response and booking_response.status_code == 200:
                                                st.success("Appointment booked successfully!")
                                                st.balloons()
                                            elif booking_response:
                                                st.error(booking_response.json().get("detail", "Booking failed"))
                                        else:
                                            st.error("Please provide a reason for the appointment")
                                else:
                                    st.warning("No available slots for this date. Please select another date.")
                else:
                    st.info("No doctors available at the moment.")

        with tab2:
            st.subheader("My Appointments")

            response = make_request("GET", "/api/v1/appointments/my")
            if response and response.status_code == 200:
                appointments = response.json()

                if appointments:
                    # Group by status
                    scheduled = [a for a in appointments if a['status'] == 'scheduled']
                    completed = [a for a in appointments if a['status'] == 'completed']
                    cancelled = [a for a in appointments if a['status'] == 'cancelled']

                    if scheduled:
                        st.write("### Upcoming Appointments")
                        for apt in scheduled:
                            with st.container():
                                col1, col2, col3 = st.columns([3, 2, 1])
                                with col1:
                                    st.write(f"**Dr. {apt['doctor']['full_name']}**")
                                    st.write(f"Date: {apt['appointment_date']} at {apt['appointment_time']}")
                                    st.write(f"Reason: {apt['reason']}")
                                with col3:
                                    if st.button("Cancel", key=f"cancel_{apt['id']}"):
                                        cancel_response = make_request(
                                            "DELETE",
                                            f"/api/v1/appointments/{apt['id']}"
                                        )
                                        if cancel_response and cancel_response.status_code == 200:
                                            st.success("Appointment cancelled")
                                            st.rerun()
                                st.divider()

                    if completed:
                        st.write("### Completed Appointments")
                        for apt in completed:
                            st.write(f"Dr. {apt['doctor']['full_name']} - {apt['appointment_date']}")

                    if cancelled:
                        st.write("### Cancelled Appointments")
                        for apt in cancelled:
                            st.write(f"Dr. {apt['doctor']['full_name']} - {apt['appointment_date']}")
                else:
                    st.info("You have no appointments yet. Book your first appointment!")