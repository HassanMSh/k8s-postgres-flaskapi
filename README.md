# Securing Kubernetes with Oauth2-proxy

## Prerequisits

+ A running local kubernetes cluster using minikube
+ An application running inside that cluster with a FQDN
+ A Github account with sudo privilege
+ For Google OAuth2.0, a top level domain is required.

_Note that the FQDN I am using is local, I have edited my host files to make this possible_

	$cat /etc/hosts
	127.0.0.1       localhost
	192.168.49.2    www.postgres.api ## minikube exposed service ip address

## Configure ingress and expose application service:

	minikube addons enable ingress
	minikube service flask-service

## Create a custom GitHub OAuth application

+ Homepage URL is the FQDN in the Ingress rule, like https://www.postgres.api
+ Authorization callback URL is the same as the base FQDN plus /oauth2/callback, like https://www.postgres.api/oauth2 (we are using this) or https://www.postgres.api/oauth2/callback

## Configure oauth2_proxy values in the file oauth2-proxy.yaml with the values:

+ OAUTH2_PROXY_CLIENT_ID with the github <Client ID>
+ OAUTH2_PROXY_CLIENT_SECRET with the github <Client Secret>
+ OAUTH2_PROXY_COOKIE_SECRET with value of python -c 'import os,base64; print(base64.b64encode(os.urandom(16)).decode("ascii"))'

### oauth2-proxy.yaml

	apiVersion: apps/v1
	kind: Deployment
	metadata:
	  labels:
	    k8s-app: oauth2-proxy
	  name: oauth2-proxy
	  namespace: kube-system
	spec:
	  replicas: 1
	  selector:
	    matchLabels:
	      k8s-app: oauth2-proxy
	  template:
	    metadata:
	      labels:
	        k8s-app: oauth2-proxy
	    spec:
	      containers:
	      - args:
	        - --provider=github
	        - --email-domain=*
	        - --upstream=file:///dev/null
	        - --http-address=0.0.0.0:4180
	        ## this line was added because there's an issue with the latest version of OAuth-proxy
	        - --scope=user:email
	        env:
	        - name: OAUTH2_PROXY_CLIENT_ID
	          value: ClientID
	        - name: OAUTH2_PROXY_CLIENT_SECRET
	          value: ClientSecret
	        # generate the coockie secret using docker run -ti --rm python:3-alpine python -c 'import secrets,base64; print(base64.b64encode(base64.b64encode(	secrets.token_bytes(16))));'
	        - name: OAUTH2_PROXY_COOKIE_SECRET
	          value: SECRET
	        image: quay.io/oauth2-proxy/oauth2-proxy:latest
	        imagePullPolicy: Always
	        name: oauth2-proxy
	        ports:
	        - containerPort: 4180
	          protocol: TCP
	
	---
	
	apiVersion: v1
	kind: Service
	metadata:
	  labels:
	    k8s-app: oauth2-proxy
	  name: oauth2-proxy
	  namespace: kube-system
	spec:
	  ports:
	  - name: http
	    port: 4180
	    protocol: TCP
	    targetPort: 4180
	  selector:
	    k8s-app: oauth2-proxy

## Customize the application-ingress.yaml for your app:

+ Replace __INGRESS_HOST__ with a valid FQDN and __INGRESS_SECRET__ with a Secret with a valid SSL certificate.

### application-ingress.yaml:

	---
	apiVersion: networking.k8s.io/v1
	
	kind: Ingress
	metadata:
	  name: flask-ingress
	  namespace: default
	  ## This part is the one responsible for redirecting users to oauth2-proxy
	  annotations:
	    nginx.ingress.kubernetes.io/auth-url: "https://$host/oauth2/auth"
	    nginx.ingress.kubernetes.io/auth-signin: "https://$host/oauth2/start?rd=$escaped_request_uri"
	spec:
	  rules:
	    - host: www.postgres.api
	      http:
	      # This is the path that will be used to access the flask app
	        paths:
	          - path: /
	            pathType: Prefix
	            backend:
	              service:
	                name: flask-service
	                port:
	                  number: 5000

### Kubernetes Secret with a valid SSL certificate

To create a Kubernetes Secret with a valid SSL certificate, you will need to obtain the certificate and private key in PEM format, and then create the Secret using the kubectl command-line tool.

Here are the steps to create a Kubernetes Secret with a valid SSL certificate:

#### Obtain the certificate and private key in PEM format. You can get these from a certificate authority (CA), or by generating a self-signed certificate.

#### Create a Kubernetes Secret with the certificate and private key using the kubectl create secret tls command. The tls type of secret is used for SSL certificates. The syntax for the command is as follows:

	kubectl create secret tls <secret-name> --cert=<path-to-certificate-file> --key=<path-to-private-key-file>

Replace <secret-name> with a unique name for your Secret, <path-to-certificate-file> with the path to the PEM-encoded certificate file, and <path-to-private-key-file> with the path to the PEM-encoded private key file.

For example, if your certificate and private key files are named mycert.pem and mykey.pem, and you want to create a Secret named my-secret, you would run the following command:

	kubectl create secret tls my-secret --cert=mycert.pem --key=mykey.pem

#### Verify that the Secret was created successfully using the kubectl describe secret command:

	kubectl describe secret <secret-name>

Replace <secret-name> with the name of your Secret. The output should show the details of the Secret, including the certificate and private key.

That's it! You now have a Kubernetes Secret with a valid SSL certificate that can be used for TLS termination in an Ingress or other Kubernetes resource.

### oauth2-ingress.yaml:

	---
	
	apiVersion: networking.k8s.io/v1
	kind: Ingress
	metadata:
	  name: oauth2-proxy
	  namespace: kube-system
	spec:
	  ingressClassName: nginx
	  rules:
	  - host: www.postgres.api
	    http:
	    ## This is the path that will be protected by oauth2-proxy
	      paths:
	      - path: /oauth2
	        pathType: Prefix
	        backend:
	          service:
	            name: oauth2-proxy
	            port:
	              number: 4180
	  tls:
	  - hosts:
	    - www.postgres.api
	    secretName: tls-secret

## Deploy the oauth2 proxy and the igress rules:

	kubectl create -f oauth2-proxy.yaml
	kubectl create -f application-ingress.yaml

## References

[Nginx Ingress External OAUTH](https://kubernetes.github.io/ingress-nginx/examples/auth/oauth-external-auth/)
[Oauth2-Proxy Issue](https://github.com/oauth2-proxy/oauth2-proxy/issues/1669)

