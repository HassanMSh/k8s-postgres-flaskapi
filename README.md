# Postgress

## Prerequisites:

+ Ubuntu 22.04 LTS
+ docker
+ minikube
+ kubectl
+ Hardware Requirements:
	* 4 CPUs or more
	* 4GB of free memory
	* 30GB of free disk space
	* Internet connection

## Create a secret:

### Encrypt the password

	echo "password" | base64

### Copy output, then create a secrets config file and apply it on the cluster:

	nano postgres-secrets.yaml

	apiVersion: v1
	kind: Secret
	metadata:
	  name: postgres-secret-config
	type: Opaque
	data:
	  password: cG9zdGdyZXM

### Apply this config:

	kubectl apply -f postgres-secrets.yaml

## Create PersistentVolume and PersistentVolumeClaim

### First, we define the configuration for the PersistentVolume:

	nano pv-volume.yaml

	apiVersion: v1
	kind: PersistentVolume
	metadata:
	  name: postgres-pv-volume
	  labels:
	    type: local
	spec:
	  storageClassName: manual
	  capacity:
	    storage: 5Gi
	  accessModes:
	    - ReadWriteOnce
	  hostPath:
	    path: "/mnt/data"

### Apply it:

	kubectl apply -f pv-volume.yaml

### Follow up with a PersistentVolumeClaim configuration that matches the details of the previous manifest:

	nano pv-claim.yaml

	apiVersion: v1
	kind: PersistentVolumeClaim
	metadata:
	  name: postgres-pv-claim
	spec:
	  storageClassName: manual
	  accessModes:
	    - ReadWriteOnce
	  resources:
	    requests:
	      storage: 1Gi

### Apply it

	kubectl apply -f pv-claim.yaml

## Create Deployment

### Issue a deployment config:

	nano postgres-deployment.yaml

	---
	apiVersion: apps/v1
	kind: Deployment
	metadata:
	  name: postgres
	  labels:
	    app: postgres
	spec:
	  replicas: 1
	  selector:
	    matchLabels:
	      app: postgres
	  template:
	    metadata:
	      labels:
	        app: postgres
	    spec:
	      volumes:
	        - name: postgres-pv-storage
	          persistentVolumeClaim:
	            claimName: postgres-pv-claim
	      containers:
	        - name: postgres
	          image: postgres:11
	          imagePullPolicy: IfNotPresent
	          ports:
	            - containerPort: 5432
	          env:
	            - name: postgres-secret-config
	              valueFrom:
	                secretKeyRef:
	                  name: postgres-secret-config
	                  key: password
	            - name: PGDATA
	              value: /var/lib/postgresql/data/pgdata
	          volumeMounts:
	            - mountPath: /var/lib/postgresql/data
	              name: postgres-pv-storage

## Create Service

### service manifest:

	nano postgres-service.yaml

	apiVersion: v1
	kind: Service
	metadata:
	  name: postgres
	  labels:
	    app: postgres
	spec:
	  type: NodePort
	  ports:
	   - name: postgres-node-port
	     port: 5432
	     protocol: TCP
	  selector:
	    app: postgres

### Apply service:

	kubectl apply -f postgres-service.yaml

## Access postgress CLI:

	kubectl exec -it postgres-podID -- psql -U postgres

## Create DB

	CREATE DATABASE flaskapi;
	\c flaskapi;
	CREATE TABLE users ( user_id SERIAL PRIMARY KEY, user_name VARCHAR(255), user_email VARCHAR(255), user_password VARCHAR(255));

## Create flask service and deployment

### Flask service

	nano flask-service.yaml

	---
	apiVersion: v1
	kind: Service
	metadata:
	  name: flask-service
	spec:
	  ports:
	  - port: 5000
	    protocol: TCP
	    targetPort: 5000
	  selector:
	    app: flaskapi
	  type: LoadBalancer

### Flask Deployment

	nano flask-deployment.yaml

	---
	apiVersion: apps/v1
	kind: Deployment
	metadata:
	  name: flaskapi-deployment
	  labels:
	    app: flaskapi
	spec:
	  replicas: 3
	  selector:
	    matchLabels:
	      app: flaskapi
	  template:
	    metadata:
	      labels:
	        app: flaskapi
	    spec:
	      containers:
	        - name: flaskapi
	          image: flask-api
	          imagePullPolicy: Never
	          ports:
	            - containerPort: 5000
	          env:
	            - name: postgres-secret-config
	              valueFrom:
	                secretKeyRef:
	                  name: postgres-secret-config
	                  key: password
	            - name: db_name
	              value: flaskapi


## Configure minikube to use local docker image

	minikube docker-env
	eval $(minikube -p minikube docker-env)

## Create flask Image in docker

To configure the API based on specific usage, you wil have to create a local docker image to use it as a pod.

### Create a Dockerfile

	nano Dockerfile

	FROM python:3.6-slim
	
	RUN apt-get clean \
	    && apt-get -y update
	
	RUN apt-get -y install \
	    nginx \
	    python3-dev \
	    build-essential
	
	WORKDIR /app
	
	COPY requirements.txt /app/requirements.txt
	RUN pip install -r requirements.txt --src /usr/local/src
	
	COPY . .
	
	EXPOSE 5000
	CMD [ "python", "flaskapi.py" ]

### Create flaskapi.py

	nano flaskapi.py

	import os
	from flask import jsonify, request, Flask
	from psycopg2 import connect
	
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
	    return "Hello, world!"
	
	@app.route("/create", methods=["POST"])
	def add_user():
	    """Function to create a user in the PostgreSQL database"""
	    json = request.json
	    name = json["name"]
	    email = json["email"]
	    pwd = json["pwd"]
	    if name and email and pwd and request.method == "POST":
	        sql = "INSERT INTO users(user_name, user_email, user_	password) " \
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
	        cursor.execute("SELECT * FROM users WHERE user_id=%s", (	user_id,))
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
	        cursor.execute("DELETE FROM users WHERE user_id=%s", (user_	id,))
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

### Create requirements.txt

	nano requirements.txt

	Flask==1.0.3  
	Flask-MySQL==1.4.0  
	PyMySQL==0.9.3
	uWSGI==2.0.17.1
	mysql-connector-python
	cryptography
	psycopg2-binary==2.9.1

### Build the Dockerfile:

	docker build . -t flask-api

## Deploying the cluster

	kubectl apply -f flask-service.yaml
	kubectl apply -f flask-deployment.yaml

## Expose the API

The API can be accessed by exposing it using minikube: 

	minikube service flask-service

This will return a URL. If you paste this to your browser you will see the hello world message. You can use this service_URL to make requests to the API

### Now you can use the API to CRUD your database

#### add a user:

	curl -H "Content-Type: application/json" -d '{"name": "<user_name>", "email": "<user_email>", "pwd": "<user_password>"}' <service_URL>/create

#### get all users:

	curl <service_URL>/users

#### get information of a specific user:

	curl <service_URL>/user/<user_id>

#### delete a user by user_id:

	curl -H "Content-Type: application/json" <service_URL>/delete/<user_id>

#### update a user's information:

	curl -H "Content-Type: application/json" -d {"name": "<user_name>", "email": "<user_email>", "pwd": "<user_password>", "user_id": <user_id>} <service_URL>/update

## Ingress configuration;

### Enable the Ingress controller

	minikube addons enable ingress

### Verify that the NGINX Ingress controller is running

	kubectl get pods -n ingress-nginx

### Create an Ingress

	nano flask-ingress.yaml

	apiVersion: networking.k8s.io/v1
	kind: Ingress
	metadata:
	  name: flask-ingress
	spec:
	  rules:
	    - host: postgres.api
	      http:
	        paths:
	          - path: /
	            pathType: Prefix
	            backend:
	              service:
	                name: flask-service
	                port:
	                  number: 5000

### Verify the IP address is set:

	kubectl get ingress

You should see an IPv4 address in the ADDRESS column; for example:

	NAME            CLASS   HOSTS          ADDRESS        PORTS   AGE
	flask-ingress   nginx   postgres.api   192.168.49.2   80      59m

### Add the following line to the bottom of the /etc/hosts file on your computer (you will need administrator access):

	192.168.49.2	postgres.api

### Verify that the Ingress controller is directing traffic:

	curl postgres.api

## References

+ [RikKraanVatage GitHub Repo](https://github.com/RikKraanVantage/kubernetes-flask-mysql)
+ [Theo Despoudis Article](https://sweetcode.io/how-to-use-kubernetes-to-deploy-postgres/)
+ [Rik Kraan Article](https://www.kdnuggets.com/2021/02/deploy-flask-api-kubernetes-connect-micro-services.html)
+ [Forketyfork](https://medium.com/swlh/how-to-run-locally-built-docker-images-in-kubernetes-b28fbc32cc1d)
+ [Kubernetes Documentation](https://kubernetes.io/docs/home/)
