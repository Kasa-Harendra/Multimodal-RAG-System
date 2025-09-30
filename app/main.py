import streamlit as st
import os
import sys
import time

# Add parent directory to path for importing utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.authentication import AuthManager, init_auth_session, check_session

# Page configuration
st.set_page_config(
    page_title="Multimodal RAG System - Authentication",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide default Streamlit page navigation
hide_pages_style = """
    <style>
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
"""
st.markdown(hide_pages_style, unsafe_allow_html=True)

# Initialize authentication
init_auth_session()

# Check for existing valid session
if check_session():
    st.success(f"✅ Welcome back, {st.session_state['user_info']['email']}!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Launch RAG System", type="primary", use_container_width=True):
            # Use query params to maintain session
            st.query_params["authenticated"] = "true"
            st.switch_page("pages/app.py")
        
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            # Logout user
            auth_manager = st.session_state['auth_manager']
            if 'session_token' in st.session_state:
                auth_manager.logout_user(st.session_state['session_token'])
            
            # Clear session state completely
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Clear query params
            st.query_params.clear()
            st.rerun()
    
    st.stop()

# Main authentication interface
st.title("🔐 Multimodal RAG System")
st.markdown("### Secure Authentication Portal")

# Get auth manager
auth_manager = st.session_state['auth_manager']

# Display system stats
col1, col2 = st.columns(2)
with col1:
    st.markdown("🔒 Security")

# Authentication tabs
t1, t2, t3 = st.tabs(["🔑 Login", "📝 Register", "🔄 Forgot Password"])

# Login Tab
with t1:
    st.markdown("#### Welcome Back!")
    
    # Create a form for login
    with st.form("login_form", clear_on_submit=False):
        login_user_name = st.text_input(
            'Email', 
            key="login-mail", 
            help="The Email ID you have registered with. If not registered till now, proceed with REGISTRATION",
            placeholder="user@example.com"
        )
        login_password = st.text_input(
            'Password', 
            key="login-pass", 
            type="password",
            help="Enter your password"
        )
        
        # Center the login button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_submitted = st.form_submit_button(
                "🔑 Login", 
                type="primary", 
                use_container_width=True
            )
    
    # Handle login submission
    if login_submitted:
        if not login_user_name or not login_password:
            st.error("❌ Please fill in all fields")
        else:
            with st.spinner("🔍 Authenticating..."):
                success, message, user_data = auth_manager.login_user(login_user_name, login_password)
                
                if success:
                    st.success(f"✅ {message}")
                    
                    # Store user session with persistent flag
                    st.session_state['authenticated'] = True
                    st.session_state['user_info'] = user_data
                    st.session_state['session_token'] = user_data['session_token']
                    st.session_state['login_time'] = time.time()  # Add timestamp
                    
                    # Show success message with countdown
                    with st.spinner("🚀 Redirecting to RAG System..."):
                        time.sleep(2)  # Brief pause to show success
                    
                    # Set query param for authentication state
                    st.query_params["authenticated"] = "true"
                    st.switch_page("pages/app.py")
                else:
                    st.error(f"❌ {message}")
    
    # Quick link to forgot password
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("🔄 **Forgot your password?** Use the 'Forgot Password' tab above")

# Register Tab with OTP verification
with t2:
    st.markdown("#### Create New Account")
    
    # Multi-step registration process
    registration_step = st.session_state.get('registration_step', 'email')
    
    # Step 1: Email and Password Entry
    if registration_step == 'email':
        st.info("📧 **Step 1:** Enter your email and password")
        
        with st.form("register_form_step1", clear_on_submit=False):
            register_user_name = st.text_input(
                'Email', 
                key="registration-mail", 
                help="Enter a valid email address. You will receive an OTP for verification.",
                placeholder="user@example.com"
            )
            register_password = st.text_input(
                'Password', 
                key="registration-pass", 
                type="password",
                help="Password must be at least 8 characters with uppercase, lowercase, and numbers"
            )
            confirm_password = st.text_input(
                'Confirm Password',
                key="confirm-pass",
                type="password",
                help="Re-enter your password to confirm"
            )
            
            # Password requirements info
            with st.expander("🔒 Password Requirements"):
                st.write("Your password must contain:")
                st.write("• At least 8 characters")
                st.write("• At least one uppercase letter (A-Z)")
                st.write("• At least one lowercase letter (a-z)")
                st.write("• At least one number (0-9)")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                send_otp_submitted = st.form_submit_button(
                    "📧 Send OTP", 
                    type="primary", 
                    use_container_width=True
                )
        
        # Handle email submission and OTP sending
        if send_otp_submitted:
            if not register_user_name or not register_password or not confirm_password:
                st.error("❌ Please fill in all fields")
            elif register_password != confirm_password:
                st.error("❌ Passwords do not match")
            else:
                with st.spinner("📧 Sending OTP to your email..."):
                    success, message = auth_manager.generate_and_send_otp(register_user_name)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("📱 Please check your email and enter the OTP below.")
                        
                        # Store email and password for next step
                        st.session_state['pending_email'] = register_user_name
                        st.session_state['pending_password'] = register_password
                        st.session_state['registration_step'] = 'otp'
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    # Step 2: OTP Verification
    elif registration_step == 'otp':
        st.info(f"📱 **Step 2:** Enter the OTP sent to **{st.session_state.get('pending_email')}**")
        
        with st.form("otp_verification_form", clear_on_submit=False):
            st.write(f"**Email:** {st.session_state.get('pending_email')}")
            
            otp_input = st.text_input(
                'Enter 6-digit OTP',
                key="otp-input",
                help="Check your email for the 6-digit verification code",
                placeholder="123456",
                max_chars=6
            )
            
            col1, col2 = st.columns(2)
            with col1:
                verify_otp_submitted = st.form_submit_button(
                    "✅ Verify OTP", 
                    type="primary", 
                    use_container_width=True
                )
            with col2:
                resend_otp_submitted = st.form_submit_button(
                    "🔄 Resend OTP", 
                    type="secondary", 
                    use_container_width=True
                )
        
        # Handle OTP verification
        if verify_otp_submitted:
            if not otp_input:
                st.error("❌ Please enter the OTP")
            elif len(otp_input) != 6:
                st.error("❌ OTP must be 6 digits")
            else:
                with st.spinner("🔍 Verifying OTP..."):
                    success, message = auth_manager.verify_otp(st.session_state['pending_email'], otp_input)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state['registration_step'] = 'complete'
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        # Handle OTP resend
        if resend_otp_submitted:
            with st.spinner("📧 Resending OTP..."):
                success, message = auth_manager.generate_and_send_otp(st.session_state['pending_email'])
                
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        
        # Option to go back
        if st.button("⬅️ Back to Email Entry"):
            st.session_state['registration_step'] = 'email'
            st.session_state['pending_email'] = None
            st.session_state['pending_password'] = None
            st.rerun()
    
    # Step 3: Complete Registration
    elif registration_step == 'complete':
        st.success("🎉 **Step 3:** Email verified! Completing registration...")
        
        with st.spinner("👤 Creating your account..."):
            time.sleep(1)  # Small delay for better UX
            success, message = auth_manager.register_user(
                st.session_state['pending_email'], 
                st.session_state['pending_password']
            )
            
            if success:
                st.success(f"✅ {message}")
                st.info("🔑 You can now login with your credentials!")
                st.balloons()
                
                # Reset registration state
                st.session_state['registration_step'] = 'email'
                st.session_state['pending_email'] = None
                st.session_state['pending_password'] = None
                
                # Auto-switch to login tab would be nice, but we'll show a button
                if st.button("🔑 Go to Login", type="primary"):
                    st.rerun()
            else:
                st.error(f"❌ {message}")
                # Reset and try again
                st.session_state['registration_step'] = 'email'
                if st.button("🔄 Try Again"):
                    st.rerun()

# Forgot Password Tab
with t3:
    st.markdown("#### Reset Your Password")
    
    # Multi-step password reset process
    reset_step = st.session_state.get('password_reset_step', 'email')
    
    # Step 1: Enter email for password reset
    if reset_step == 'email':
        st.info("📧 **Step 1:** Enter your registered email address")
        
        with st.form("forgot_password_form", clear_on_submit=False):
            reset_email = st.text_input(
                'Email Address', 
                key="reset-email", 
                help="Enter the email address associated with your account",
                placeholder="user@example.com"
            )
            
            st.write("🔒 We'll send you a secure code to reset your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                send_reset_otp_submitted = st.form_submit_button(
                    "📧 Send Reset Code", 
                    type="primary", 
                    use_container_width=True
                )
        
        # Handle password reset OTP sending
        if send_reset_otp_submitted:
            if not reset_email:
                st.error("❌ Please enter your email address")
            else:
                with st.spinner("📧 Sending password reset code..."):
                    success, message = auth_manager.generate_password_reset_otp(reset_email)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("📱 Please check your email and enter the reset code below.")
                        
                        # Store email for next step
                        st.session_state['reset_email'] = reset_email
                        st.session_state['password_reset_step'] = 'verify_otp'
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    # Step 2: Verify reset OTP
    elif reset_step == 'verify_otp':
        st.info(f"📱 **Step 2:** Enter the reset code sent to **{st.session_state.get('reset_email')}**")
        
        with st.form("verify_reset_otp_form", clear_on_submit=False):
            st.write(f"**Email:** {st.session_state.get('reset_email')}")
            
            reset_otp_input = st.text_input(
                'Enter 6-digit Reset Code',
                key="reset-otp-input",
                help="Check your email for the 6-digit password reset code",
                placeholder="123456",
                max_chars=6
            )
            
            col1, col2 = st.columns(2)
            with col1:
                verify_reset_otp_submitted = st.form_submit_button(
                    "✅ Verify Code", 
                    type="primary", 
                    use_container_width=True
                )
            with col2:
                resend_reset_otp_submitted = st.form_submit_button(
                    "🔄 Resend Code", 
                    type="secondary", 
                    use_container_width=True
                )
        
        # Handle reset OTP verification
        if verify_reset_otp_submitted:
            if not reset_otp_input:
                st.error("❌ Please enter the reset code")
            elif len(reset_otp_input) != 6:
                st.error("❌ Reset code must be 6 digits")
            else:
                with st.spinner("🔍 Verifying reset code..."):
                    success, message = auth_manager.verify_password_reset_otp(
                        st.session_state['reset_email'], 
                        reset_otp_input
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state['password_reset_step'] = 'new_password'
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        # Handle reset OTP resend
        if resend_reset_otp_submitted:
            with st.spinner("📧 Resending reset code..."):
                success, message = auth_manager.generate_password_reset_otp(st.session_state['reset_email'])
                
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        
        # Option to go back
        if st.button("⬅️ Back to Email Entry"):
            st.session_state['password_reset_step'] = 'email'
            st.session_state['reset_email'] = None
            st.rerun()
    
    # Step 3: Set new password
    elif reset_step == 'new_password':
        st.success("🔓 **Step 3:** Create your new password")
        
        with st.form("new_password_form", clear_on_submit=True):
            st.write(f"**Account:** {st.session_state.get('reset_email')}")
            
            new_password = st.text_input(
                'New Password',
                key="new-password",
                type="password",
                help="Create a strong password with at least 8 characters"
            )
            
            confirm_new_password = st.text_input(
                'Confirm New Password',
                key="confirm-new-password",
                type="password",
                help="Re-enter your new password to confirm"
            )
            
            # Password requirements info
            with st.expander("🔒 Password Requirements"):
                st.write("Your new password must contain:")
                st.write("• At least 8 characters")
                st.write("• At least one uppercase letter (A-Z)")
                st.write("• At least one lowercase letter (a-z)")
                st.write("• At least one number (0-9)")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                reset_password_submitted = st.form_submit_button(
                    "🔐 Reset Password", 
                    type="primary", 
                    use_container_width=True
                )
        
        # Handle password reset
        if reset_password_submitted:
            if not new_password or not confirm_new_password:
                st.error("❌ Please fill in all fields")
            elif new_password != confirm_new_password:
                st.error("❌ Passwords do not match")
            else:
                with st.spinner("🔐 Resetting your password..."):
                    success, message = auth_manager.reset_password(
                        st.session_state['reset_email'], 
                        new_password
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        
                        # Reset password reset state
                        st.session_state['password_reset_step'] = 'email'
                        st.session_state['reset_email'] = None
                        
                        # Show login button
                        st.info("🔑 You can now login with your new password!")
                        if st.button("🔑 Go to Login", type="primary"):
                            st.rerun()
                    else:
                        st.error(f"❌ {message}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <small>🛡️ Your data is securely stored with email verification and password reset protection</small>
    </div>
    """,
    unsafe_allow_html=True
)