import os
from flask import jsonify, request, Flask
from psycopg2 import connect
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# PostgreSQL configurations
db_user = "postgres"
db_password = os.getenv("postgres-secret-config")
db_name = os.getenv("db_name")
db_host = os.getenv("POSTGRES_SERVICE_HOST")
db_port = int(os.getenv("POSTGRES_SERVICE_PORT"))

def create_connection():
    """Helper function to create a PostgreSQL connection"""
    return connect(user=db_user, password=db_password, dbname=db_name, host=db_host, port=db_port)

@app.route("/")
def index():
    """Function to test the functionality of the API"""
    return "Hello, world! :)"

@app.route("/create", methods=["POST"])
def add_user():
    """Function to create a user in the PostgreSQL database"""
    json = request.json
    name = json["name"]
    email = json["email"]
    pwd = json["pwd"]
    if name and email and pwd and request.method == "POST":
        sql = "INSERT INTO users(user_name, user_email, user_password) " \
              "VALUES(%s, %s, %s)"
        data = (name, email, pwd)
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute(sql, data)
            conn.commit()
            cursor.close()
            conn.close()
            resp = jsonify("User created successfully!")
            resp.status_code = 200
            return resp
        except Exception as exception:
            return jsonify(str(exception))
    else:
        return jsonify("Please provide name, email and pwd")

@app.route("/users", methods=["GET"])
def users():
    """Function to retrieve all users from the PostgreSQL 	database"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        resp = jsonify(rows)
        resp.status_code = 200
        return resp
    except Exception as exception:
        return jsonify(str(exception))

@app.route("/user/<int:user_id>", methods=["GET"])
def user(user_id):
    """Function to get information of a specific user in the 	PostgreSQL database"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        resp = jsonify(row)
        resp.status_code = 200
        return resp
    except Exception as exception:
        return jsonify(str(exception))

@app.route("/update", methods=["POST"])
def update_user():
    """Function to update a user in the PostgreSQL database"""
    json = request.json
    name = json["name"]
    email = json["email"]
    pwd = json["pwd"]
    user_id = json["user_id"]
    if name and email and pwd and user_id and request.method == 	"POST":
        sql = "UPDATE users SET user_name=%s, user_email=%s, " \
              "user_password=%s WHERE user_id=%s"
        data = (name, email, pwd, user_id)
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute(sql, data)
            conn.commit()
            cursor.close()
            conn.close()
            resp = jsonify("User updated successfully!")
            resp.status_code = 200
            return resp
        except Exception as exception:
            return jsonify(str(exception))
    else:
        return jsonify("Please provide id, name, email and pwd")

@app.route("/delete/<int:user_id>")
def delete_user(user_id):
    """Function to delete a user from the PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        resp = jsonify("User deleted successfully!")
        resp.status_code = 200
        return resp
    except Exception as exception:
        return jsonify(str(exception))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
