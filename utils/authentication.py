import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import secrets
import streamlit as st
import smtplib
import random
import string
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# load_dotenv()

class AuthManager:
    """File-based authentication manager using SQLite with OTP verification"""
    
    def __init__(self, db_path="data/users.db"):
        """Initialize authentication manager with database path"""
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Run migrations to ensure schema is up to date
        self._run_migrations()
    
    def _init_database(self):
        """Initialize the users database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_verified BOOLEAN DEFAULT 0
                )
            ''')
            
            # Create sessions table for login sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create OTP table for email verification
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_otps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    otp_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_used BOOLEAN DEFAULT 0,
                    attempts INTEGER DEFAULT 0
                )
            ''')
            
            # Create schema_migrations table to track migrations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def _run_migrations(self):
        """Run database migrations to update schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if is_verified column exists in users table
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_verified' not in columns:
                # Add is_verified column to existing users table
                cursor.execute('''
                    ALTER TABLE users 
                    ADD COLUMN is_verified BOOLEAN DEFAULT 0
                ''')
                
                # Mark migration as applied
                cursor.execute('''
                    INSERT OR IGNORE INTO schema_migrations (migration_name) 
                    VALUES ('add_is_verified_column')
                ''')
                
                print("✅ Migration applied: Added is_verified column to users table")
            
            # Migration: Set existing users as verified (for backward compatibility)
            migration_name = 'set_existing_users_verified'
            cursor.execute('''
                SELECT COUNT(*) FROM schema_migrations 
                WHERE migration_name = ?
            ''', (migration_name,))
            
            if cursor.fetchone()[0] == 0:
                # Set existing users as verified if they don't have OTP records
                cursor.execute('''
                    UPDATE users 
                    SET is_verified = 1 
                    WHERE id NOT IN (
                        SELECT DISTINCT u.id 
                        FROM users u 
                        INNER JOIN email_otps otp ON LOWER(u.email) = LOWER(otp.email)
                    )
                ''')
                
                # Mark migration as applied
                cursor.execute('''
                    INSERT INTO schema_migrations (migration_name) 
                    VALUES (?)
                ''', (migration_name,))
                
                print("✅ Migration applied: Set existing users as verified")
            
            conn.commit()
    
    def _generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def _send_otp_email(self, email: str, otp: str) -> bool:
        """Send OTP via email"""
        try:
            # smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            # smtp_port = int(os.getenv('SMTP_PORT', '587'))
            # sender_email = os.getenv('SENDER_EMAIL', 'your-app@gmail.com')
            # sender_password = os.getenv('SENDER_PASSWORD', 'your-app-password')
            
            smtp_server = st.secrets.get('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(st.secrets.get('SMTP_PORT', '587'))
            sender_email = st.secrets.get('SENDER_EMAIL', 'your-app@gmail.com')
            sender_password = st.secrets.get('SENDER_PASSWORD', 'your-app-password')
            
            # Demo mode check
            if not all([sender_email != 'your-app@gmail.com', sender_password != 'your-app-password']):
                print(f"📧 DEMO MODE - OTP for {email}: {otp}")
                return True
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = "🔐 Multimodal RAG System - Email Verification"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>🔐 Email Verification</h2>
                <p>Hello,</p>
                <p>Thank you for registering with Multimodal RAG System!</p>
                <p>Your verification code is:</p>
                <h1 style="color: #007bff; text-align: center; background: #f8f9fa; padding: 20px; border-radius: 5px;">
                    {otp}
                </h1>
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This code expires in 10 minutes</li>
                    <li>Don't share this code with anyone</li>
                    <li>Enter this code in the registration form to complete your account setup</li>
                </ul>
                <p>If you didn't request this registration, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Multimodal RAG System Team</p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            return True
            
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def generate_and_send_otp(self, email: str) -> tuple:
        """Generate and send OTP to email"""
        try:
            # Validate email format
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            # Check if user already exists
            if self.user_exists(email):
                return False, "User with this email already exists"
            
            # Generate OTP
            otp = self._generate_otp()
            expires_at = datetime.now() + timedelta(minutes=10)  # OTP expires in 10 minutes
            
            # Store OTP in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete any existing OTPs for this email
                cursor.execute('DELETE FROM email_otps WHERE email = ?', (email.lower(),))
                
                # Insert new OTP
                cursor.execute('''
                    INSERT INTO email_otps (email, otp_code, expires_at)
                    VALUES (?, ?, ?)
                ''', (email.lower(), otp, expires_at))
                
                conn.commit()
            
            # Send OTP email
            if self._send_otp_email(email, otp):
                return True, "OTP sent successfully! Check your email."
            else:
                return False, "Failed to send OTP. Please try again."
                
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_otp(self, email: str, otp: str) -> tuple:
        """Verify OTP for email"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the latest OTP for this email
                cursor.execute('''
                    SELECT id, otp_code, expires_at, is_used, attempts
                    FROM email_otps 
                    WHERE email = ? AND is_used = 0
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (email.lower(),))
                
                otp_data = cursor.fetchone()
                
                if not otp_data:
                    return False, "No OTP found or OTP already used"
                
                otp_id, stored_otp, expires_at, is_used, attempts = otp_data
                
                # Check expiration
                if datetime.now() > datetime.fromisoformat(expires_at):
                    return False, "OTP has expired. Please request a new one."
                
                # Check attempts (max 3 attempts)
                if attempts >= 3:
                    return False, "Too many failed attempts. Please request a new OTP."
                
                # Verify OTP
                if otp.strip() == stored_otp:
                    # Mark OTP as used
                    cursor.execute('''
                        UPDATE email_otps 
                        SET is_used = 1 
                        WHERE id = ?
                    ''', (otp_id,))
                    conn.commit()
                    return True, "OTP verified successfully!"
                else:
                    # Increment attempts
                    cursor.execute('''
                        UPDATE email_otps 
                        SET attempts = attempts + 1 
                        WHERE id = ?
                    ''', (otp_id,))
                    conn.commit()
                    remaining_attempts = 3 - (attempts + 1)
                    return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
                    
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"OTP verification failed: {str(e)}"
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Create password hash using SHA-256 with salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> tuple:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"
    
    def register_user(self, email: str, password: str) -> tuple:
        """Register a new user (requires prior OTP verification)"""
        try:
            # Validate email format
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            # Validate password strength
            is_valid, msg = self._validate_password(password)
            if not is_valid:
                return False, msg
            
            # Check if user already exists
            if self.user_exists(email):
                return False, "User with this email already exists"
            
            # Check if email is verified (has used OTP)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM email_otps 
                    WHERE email = ? AND is_used = 1
                ''', (email.lower(),))
                
                verified_count = cursor.fetchone()[0]
                if verified_count == 0:
                    return False, "Email not verified. Please verify your email with OTP first."
            
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Insert user into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (email, password_hash, salt, created_at, is_verified)
                    VALUES (?, ?, ?, ?, 1)
                ''', (email.lower(), password_hash, salt, datetime.now()))
                
                conn.commit()
                return True, "User registered successfully!"
        
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def login_user(self, email: str, password: str) -> tuple:
        """Authenticate user login"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user data - handle missing is_verified column gracefully
                try:
                    cursor.execute('''
                        SELECT id, email, password_hash, salt, is_active, is_verified
                        FROM users 
                        WHERE email = ? AND is_active = 1
                    ''', (email.lower(),))
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        user_id, stored_email, stored_hash, salt, is_active, is_verified = user_data
                    else:
                        return False, "Invalid email or password", None
                        
                except sqlite3.OperationalError as e:
                    if "no such column: is_verified" in str(e):
                        # Fallback for databases without is_verified column
                        cursor.execute('''
                            SELECT id, email, password_hash, salt, is_active
                            FROM users 
                            WHERE email = ? AND is_active = 1
                        ''', (email.lower(),))
                        user_data = cursor.fetchone()
                        
                        if user_data:
                            user_id, stored_email, stored_hash, salt, is_active = user_data
                            is_verified = True  # Assume existing users are verified
                        else:
                            return False, "Invalid email or password", None
                    else:
                        raise e
                
                if not is_verified:
                    return False, "Email not verified. Please complete registration.", None
                
                # Verify password
                password_hash, _ = self._hash_password(password, salt)
                
                if password_hash != stored_hash:
                    return False, "Invalid email or password", None
                
                # Update last login
                cursor.execute('''
                    UPDATE users 
                    SET last_login = ? 
                    WHERE id = ?
                ''', (datetime.now(), user_id))
                
                # Create session token
                session_token = self._create_session(user_id)
                
                conn.commit()
                
                return True, "Login successful!", {
                    'user_id': user_id,
                    'email': stored_email,
                    'session_token': session_token
                }
        
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}", None
        except Exception as e:
            return False, f"Login failed: {str(e)}", None
    
    def user_exists(self, email: str) -> bool:
        """Check if user exists in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE email = ?', (email.lower(),))
                return cursor.fetchone() is not None
        except sqlite3.Error:
            return False
    
    def _create_session(self, user_id: int) -> str:
        """Create a new session token for user"""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)  # Session expires in 7 days
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Deactivate old sessions for this user
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE user_id = ? AND is_active = 1
                ''', (user_id,))
                
                # Create new session
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, session_token, expires_at))
                
                conn.commit()
                return session_token
        
        except sqlite3.Error:
            return None
    
    def validate_session(self, session_token: str) -> tuple:
        """Validate session token and return user info"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.id, u.email, s.expires_at
                    FROM users u
                    JOIN user_sessions s ON u.id = s.user_id
                    WHERE s.session_token = ? AND s.is_active = 1 AND s.expires_at > ?
                ''', (session_token, datetime.now()))
                
                session_data = cursor.fetchone()
                
                if session_data:
                    user_id, email, expires_at = session_data
                    return True, {
                        'user_id': user_id,
                        'email': email,
                        'expires_at': expires_at
                    }
                else:
                    return False, None
        
        except sqlite3.Error:
            return False, None
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE session_token = ?
                ''', (session_token,))
                
                conn.commit()
                return True
        
        except sqlite3.Error:
            return False
    
    def get_user_count(self) -> int:
        """Get total number of registered users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Handle missing is_verified column gracefully
                try:
                    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_verified = 1')
                    return cursor.fetchone()[0]
                except sqlite3.OperationalError as e:
                    if "no such column: is_verified" in str(e):
                        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
                        return cursor.fetchone()[0]
                    else:
                        raise e
        except sqlite3.Error:
            return 0
    
    def get_user_info(self, user_id: int) -> dict:
        """Get user information by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, email, created_at, last_login
                    FROM users 
                    WHERE id = ? AND is_active = 1
                ''', (user_id,))
                
                user_data = cursor.fetchone()
                
                if user_data:
                    return {
                        'id': user_data[0],
                        'email': user_data[1],
                        'created_at': user_data[2],
                        'last_login': user_data[3]
                    }
                return None
        
        except sqlite3.Error:
            return None
    
    def generate_password_reset_otp(self, email: str) -> tuple:
        """Generate and send OTP for password reset"""
        try:
            # Validate email format
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            # Check if user exists and is verified
            if not self.user_exists(email):
                return False, "No account found with this email address"
            
            # Check if user is verified
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        SELECT is_verified FROM users 
                        WHERE email = ? AND is_active = 1
                    ''', (email.lower(),))
                    user_data = cursor.fetchone()
                    
                    if not user_data or not user_data[0]:
                        return False, "Account not verified. Please complete registration first."
                        
                except sqlite3.OperationalError as e:
                    if "no such column: is_verified" in str(e):
                        # Assume verified for older databases
                        pass
                    else:
                        raise e
            
            # Generate OTP
            otp = self._generate_otp()
            expires_at = datetime.now() + timedelta(minutes=15)  # Password reset OTP expires in 15 minutes
            
            # Store OTP in database with special type for password reset
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete any existing password reset OTPs for this email
                cursor.execute('''
                    DELETE FROM email_otps 
                    WHERE email = ? AND otp_code LIKE 'RESET_%'
                ''', (email.lower(),))
                
                # Insert new password reset OTP (prefix with RESET_ to differentiate)
                cursor.execute('''
                    INSERT INTO email_otps (email, otp_code, expires_at)
                    VALUES (?, ?, ?)
                ''', (email.lower(), f"RESET_{otp}", expires_at))
                
                conn.commit()
            
            # Send password reset OTP email
            if self._send_password_reset_email(email, otp):
                return True, "Password reset OTP sent successfully! Check your email."
            else:
                return False, "Failed to send password reset OTP. Please try again."
                
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send password reset OTP: {str(e)}"
    
    def _send_password_reset_email(self, email: str, otp: str) -> bool:
        """Send password reset OTP via email"""
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            sender_email = os.getenv('SENDER_EMAIL', 'your-app@gmail.com')
            sender_password = os.getenv('SENDER_PASSWORD', 'your-app-password')
            
            # Demo mode check
            if not all([sender_email != 'your-app@gmail.com', sender_password != 'your-app-password']):
                print(f"📧 DEMO MODE - Password Reset OTP for {email}: {otp}")
                return True
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = "🔐 Multimodal RAG System - Password Reset"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>🔐 Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password for your Multimodal RAG System account.</p>
                <p>Your password reset verification code is:</p>
                <h1 style="color: #dc3545; text-align: center; background: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #dc3545;">
                    {otp}
                </h1>
                <p><strong>Important Security Information:</strong></p>
                <ul>
                    <li><strong>This code expires in 15 minutes</strong></li>
                    <li>Don't share this code with anyone</li>
                    <li>Only use this code if you requested a password reset</li>
                    <li>If you didn't request this reset, please ignore this email</li>
                </ul>
                <p><strong>Next Steps:</strong></p>
                <ol>
                    <li>Return to the password reset page</li>
                    <li>Enter this verification code</li>
                    <li>Create your new secure password</li>
                </ol>
                <hr>
                <p><small><strong>Security Tip:</strong> Make sure your new password is strong with at least 8 characters, including uppercase, lowercase letters, and numbers.</small></p>
                <br>
                <p>Best regards,<br>Multimodal RAG System Security Team</p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            return True
            
        except Exception as e:
            print(f"Password reset email sending failed: {e}")
            return False
    
    def verify_password_reset_otp(self, email: str, otp: str) -> tuple:
        """Verify OTP for password reset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the latest password reset OTP for this email
                cursor.execute('''
                    SELECT id, otp_code, expires_at, is_used, attempts
                    FROM email_otps 
                    WHERE email = ? AND otp_code LIKE 'RESET_%' AND is_used = 0
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (email.lower(),))
                
                otp_data = cursor.fetchone()
                
                if not otp_data:
                    return False, "No password reset OTP found or OTP already used"
                
                otp_id, stored_otp, expires_at, is_used, attempts = otp_data
                
                # Remove RESET_ prefix for comparison
                stored_otp_clean = stored_otp.replace('RESET_', '')
                
                # Check expiration
                if datetime.now() > datetime.fromisoformat(expires_at):
                    return False, "Password reset OTP has expired. Please request a new one."
                
                # Check attempts (max 3 attempts)
                if attempts >= 3:
                    return False, "Too many failed attempts. Please request a new password reset OTP."
                
                # Verify OTP
                if otp.strip() == stored_otp_clean:
                    # Mark OTP as used
                    cursor.execute('''
                        UPDATE email_otps 
                        SET is_used = 1 
                        WHERE id = ?
                    ''', (otp_id,))
                    conn.commit()
                    return True, "Password reset OTP verified successfully!"
                else:
                    # Increment attempts
                    cursor.execute('''
                        UPDATE email_otps 
                        SET attempts = attempts + 1 
                        WHERE id = ?
                    ''', (otp_id,))
                    conn.commit()
                    remaining_attempts = 3 - (attempts + 1)
                    return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
                
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Password reset OTP verification failed: {str(e)}"
    
    def reset_password(self, email: str, new_password: str) -> tuple:
        """Reset user password after OTP verification"""
        try:
            # Validate email format
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            # Validate new password strength
            is_valid, msg = self._validate_password(new_password)
            if not is_valid:
                return False, msg
            
            # Check if user exists
            if not self.user_exists(email):
                return False, "No account found with this email address"
            
            # Verify that password reset OTP was used (security check)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for recent used password reset OTP (within last 30 minutes)
                cursor.execute('''
                    SELECT COUNT(*) FROM email_otps 
                    WHERE email = ? AND otp_code LIKE 'RESET_%' AND is_used = 1
                    AND created_at > datetime('now', '-30 minutes')
                ''', (email.lower(),))
                
                recent_reset_count = cursor.fetchone()[0]
                if recent_reset_count == 0:
                    return False, "Password reset not authorized. Please verify OTP first."
            
            # Hash new password
            password_hash, salt = self._hash_password(new_password)
            
            # Update user password in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, salt = ?, last_login = ?
                    WHERE email = ? AND is_active = 1
                ''', (password_hash, salt, datetime.now(), email.lower()))
                
                # Deactivate all existing sessions for security
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE user_id = (
                        SELECT id FROM users WHERE email = ?
                    )
                ''', (email.lower(),))
                
                # Clean up used password reset OTPs
                cursor.execute('''
                    DELETE FROM email_otps 
                    WHERE email = ? AND otp_code LIKE 'RESET_%'
                ''', (email.lower(),))
                
                conn.commit()
                return True, "Password reset successfully! Please login with your new password."
        
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Password reset failed: {str(e)}"
    
# Streamlit integration functions
def init_auth_session():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user_info' not in st.session_state:
        st.session_state['user_info'] = None
    if 'auth_manager' not in st.session_state:
        st.session_state['auth_manager'] = AuthManager()
    if 'registration_step' not in st.session_state:
        st.session_state['registration_step'] = 'email'  # email -> otp -> complete
    if 'pending_email' not in st.session_state:
        st.session_state['pending_email'] = None
    # Add these new lines for password reset functionality
    if 'password_reset_step' not in st.session_state:
        st.session_state['password_reset_step'] = 'email'  # email -> verify_otp -> new_password
    if 'reset_email' not in st.session_state:
        st.session_state['reset_email'] = None

def require_auth():
    """Decorator to require authentication for a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get('authenticated', False):
                st.error("🔒 Please login to access this feature")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def check_session():
    """Check if current session is valid"""
    if 'session_token' in st.session_state and st.session_state['session_token']:
        auth_manager = st.session_state.get('auth_manager', AuthManager())
        is_valid, user_info = auth_manager.validate_session(st.session_state['session_token'])
        
        if is_valid:
            st.session_state['authenticated'] = True
            st.session_state['user_info'] = user_info
            return True
        else:
            # Session expired or invalid
            st.session_state['authenticated'] = False
            st.session_state['user_info'] = None
            st.session_state['session_token'] = None
            return False
    return False