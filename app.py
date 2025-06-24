from flask import Flask, jsonify, request
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# PostgreSQL connection details (use environment variables for security)
DB_HOST = os.environ.get('DB_HOST') or os.environ.get('DATABASE_HOST', 'gondola.proxy.rlwy.net')
DB_PORT = os.environ.get('DB_PORT') or os.environ.get('DATABASE_PORT', '46284')
DB_NAME = os.environ.get('DB_NAME') or os.environ.get('DATABASE_NAME', 'railway')
DB_USER = os.environ.get('DB_USER') or os.environ.get('DATABASE_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS') or os.environ.get('DATABASE_PASSWORD', 'PUT_YOUR_PASSWORD_HERE')

def test_database_connection():
    """Test if we can connect to the database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()
        cur.close()
        conn.close()
        return True, f"Connected to PostgreSQL: {version[0]}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if Flask and database are working"""
    db_connected, db_message = test_database_connection()
    return jsonify({
        'message': 'Flask API is running!',
        'database_connected': db_connected,
        'database_message': db_message,
        'environment_vars': {
            'DB_HOST': DB_HOST,
            'DB_PORT': DB_PORT,
            'DB_NAME': DB_NAME,
            'DB_USER': DB_USER,
            'DB_PASS': '***' if DB_PASS else 'NOT SET'
        }
    }), 200

@app.route('/students', methods=['GET'])
def get_students():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute('SELECT * FROM students LIMIT 10')  # Limit to 10 for testing
        columns = [desc[0] for desc in cur.description]
        students = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({
            'students': students, 
            'count': len(students),
            'message': f'Successfully retrieved {len(students)} students'
        }), 200
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve students from database'
        }), 500

@app.route('/students', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        # Required fields for user and student
        required_user_fields = ['username', 'email']
        required_student_fields = ['first_name', 'grade_level']
        for field in required_user_fields + required_student_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        username = data['username']
        email = data['email']
        password_hash = 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'  # demo hash
        role = 'student'
        first_name = data['first_name']
        last_name = data.get('last_name', '')
        grade_level = data['grade_level']
        date_of_birth = data.get('date_of_birth')
        enrollment_date = data.get('enrollment_date')
        phone = data.get('phone')
        address = data.get('address')
        emergency_contact = data.get('emergency_contact')
        emergency_phone = data.get('emergency_phone')
        # Connect to DB
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        # Insert user
        cur.execute("""
            INSERT INTO users (username, password_hash, email, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING user_id
        """, (username, password_hash, email, role))
        user_id = cur.fetchone()
        if user_id:
            user_id = user_id[0]
        else:
            cur.execute("SELECT user_id FROM users WHERE username=%s", (username,))
            user_id = cur.fetchone()[0]
        # Insert student
        cur.execute("""
            INSERT INTO students (user_id, first_name, last_name, grade_level, date_of_birth, enrollment_date, phone, address, emergency_contact, emergency_phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING student_id
        """, (user_id, first_name, last_name, grade_level, date_of_birth, enrollment_date, phone, address, emergency_contact, emergency_phone))
        student_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Student added successfully', 'student_id': student_id, 'user_id': user_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Fixed PUT route with better error handling
@app.route('/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student by ID"""
    print(f"PUT request received for student_id: {student_id}")
    print("Headers received:", dict(request.headers))
    print("Body received:", request.get_data())
    
    try:
        data = request.get_json()
        print("Parsed JSON data:", data)
        # List of fields you allow to update
        allowed_fields = [
            'first_name', 'last_name', 'date_of_birth', 'grade_level',
            'enrollment_date', 'phone', 'address', 'emergency_contact', 'emergency_phone', 'user_id'
        ]
        # Build the SET part of the SQL dynamically
        set_clauses = []
        values = []
        for field in allowed_fields:
            if field in data:
                value = data[field]
                # Convert empty strings to None (NULL in SQL)
                if value == "":
                    value = None
                set_clauses.append(f"{field} = %s")
                values.append(value)
        if not set_clauses:
            return jsonify({'error': 'No valid fields to update'}), 400
        values.append(student_id)
        set_clause = ', '.join(set_clauses)
        sql = f"UPDATE students SET {set_clause} WHERE student_id = %s"
        print("Executing SQL:", sql)
        print("With values:", values)
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': f'Student {student_id} updated successfully'}), 200
    except Exception as e:
        print("Database error:", str(e))
        return jsonify({'error': str(e)}), 500

# Add a GET route for individual students to help with debugging
@app.route('/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student by ID"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute('SELECT * FROM students WHERE student_id = %s', (student_id,))
        student_data = cur.fetchone()
        
        if not student_data:
            cur.close()
            conn.close()
            return jsonify({'error': f'Student with ID {student_id} not found'}), 404
        
        columns = [desc[0] for desc in cur.description]
        student = dict(zip(columns, student_data))
        cur.close()
        conn.close()
        
        return jsonify({
            'student': student,
            'message': f'Successfully retrieved student {student_id}'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': f'Failed to retrieve student {student_id} from database'
        }), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'School Database API is running!',
        'endpoints': {
            'home': '/',
            'test': '/test (test database connection)',
            'debug': '/debug (debug environment variables)',
            'students': '/students (get students data)',
            'student_by_id': '/students/<id> (get/update specific student)'
        },
        'status': 'API is ready to use'
    }), 200

# Add a route to list all available routes for debugging
@app.route('/routes', methods=['GET'])
def list_routes():
    """List all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify({
        'message': 'Available routes',
        'routes': routes
    }), 200

@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check environment variables"""
    return jsonify({
        'message': 'Debug information',
        'environment_vars': {
            'PORT': os.environ.get('PORT', 'NOT SET'),
            'DB_HOST': os.environ.get('DB_HOST', 'NOT SET'),
            'DB_PORT': os.environ.get('DB_PORT', 'NOT SET'),
            'DB_NAME': os.environ.get('DB_NAME', 'NOT SET'),
            'DB_USER': os.environ.get('DB_USER', 'NOT SET'),
            'DB_PASS': '***' if os.environ.get('DB_PASS') else 'NOT SET',
            'DATABASE_HOST': os.environ.get('DATABASE_HOST', 'NOT SET'),
            'DATABASE_PORT': os.environ.get('DATABASE_PORT', 'NOT SET'),
            'DATABASE_NAME': os.environ.get('DATABASE_NAME', 'NOT SET'),
            'DATABASE_USER': os.environ.get('DATABASE_USER', 'NOT SET'),
            'DATABASE_PASSWORD': '***' if os.environ.get('DATABASE_PASSWORD') else 'NOT SET'
        },
        'all_env_vars': {k: v for k, v in os.environ.items() if 'DB' in k or 'DATABASE' in k or 'PORT' in k}
    }), 200

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Available endpoints:")
    print("- / (home)")
    print("- /test (test database connection)")
    print("- /students (get students data)")
    print("- /students/<id> (get/update specific student)")
    print("- /routes (list all routes)")
    print("- /debug (debug information)")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)