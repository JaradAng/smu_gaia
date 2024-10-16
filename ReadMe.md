README
Project Name: GAIA - Scalable Task Processing System
Welcome to the GAIA project! This system is designed to coordinate multiple tools for processing tasks using Celery and Docker containers. It includes an autoscaler to dynamically adjust the number of worker containers based on the workload. This README provides step-by-step instructions on how to set up and run the system after cloning the repository.

Table of Contents
Prerequisites
Getting Started
Clone the Repository
Environment Variables
Directory Structure
Setup and Installation
Install Docker
Install Docker Compose
Building the Docker Images
Running the Application
Starting the Services
Accessing the Logs
Testing the System
Scaling the Services
Simulate Load
Check Running Containers
Stopping the Application
Troubleshooting
Common Issues
Logs and Debugging
Contributing
License
Additional Information
Project Components
Services Overview
Contact
Prerequisites
Before you begin, ensure you have the following installed on your system:

Git
Docker
Docker Compose
Optional (for development and testing):
Python 3.9+
pip
Getting Started
Clone the Repository
Clone the repository to your local machine using Git:

bash
Copy code
git clone https://github.com/yourusername/gaia.git
Replace yourusername with the actual GitHub username or repository path.


Directory Structure
Ensure your directory structure resembles the following:

css
Copy code
gaia/
├── docker-compose.yml
├── .env
├── main.py
├── tasks.py
├── autoscaler.py
├── container_manager.py
├── requirements.txt
├── utils/
│   ├── monitoring.py
│   └── db.py
├── chunker/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── llm/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── vector_db/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── graph_db/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── prompt/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
└── README.md
Setup and Installation
Install Docker
Follow the official Docker installation guide for your operating system:

Docker Installation
Install Docker Compose
Follow the official Docker Compose installation guide:

Docker Compose Installation
Building the Docker Images
Navigate to the root directory of the project and build the Docker images using Docker Compose:

bash
Copy code
docker-compose build
This command builds all the services defined in your docker-compose.yml file.

Running the Application
Starting the Services
Start the application using Docker Compose:

bash
Copy code
docker-compose up
This command starts all the services and displays the logs in your terminal.

If you want to run the services in detached mode (in the background), use:

bash
Copy code
docker-compose up -d
Accessing the Logs
To view the logs of the running services:

bash
Copy code
docker-compose logs -f
You can view logs for a specific service:

bash
Copy code
docker-compose logs -f <service_name>
Replace <service_name> with the name of the service (e.g., gaia, chunker, llm).

Testing the System
The system includes a test function that sends test messages to all tools. This function is invoked automatically when the main.py script runs.

To run the test manually, you can execute the following steps:

Execute the Test Function

If the application is running, the test should have executed automatically. Check the logs for the "GAIA communication test completed" message.

Verify the Results

The test results are printed in the logs. You should see output similar to:

vbnet
Copy code
Test Results:
chunker: ['Chunk 1', 'Chunk 2', 'Chunk 3']
vector_db: Vector DB processed: This is a test message from GAIA
graph_db: Graph DB processed: This is a test message from GAIA
llm: LLM generated response for: This is a test message from GAIA
prompt: Enhanced prompt: This is a test message from GAIA
Scaling the Services
The system includes an autoscaler that adjusts the number of worker containers based on the queue length. By default, it scales the llm and chunker services.

Simulate Load
To test the scaling functionality:

Enqueue Multiple Tasks

You can modify the run_test() function in main.py to enqueue multiple tasks or create a separate script to enqueue tasks to the Celery queues.

Monitor the Autoscaler

The autoscaler runs in a separate thread and adjusts the number of containers accordingly.

Check Running Containers
List the running containers to see if new worker containers have been started:

bash
Copy code
docker ps
Stopping the Application
To stop the running services:

bash
Copy code
docker-compose down
This command stops and removes all the containers created by Docker Compose.

Troubleshooting
Common Issues
Docker Permission Denied

If you encounter permission issues with Docker commands, try running with sudo or adjust your user permissions.

Port Conflicts

Ensure that the ports used in docker-compose.yml are not in use by other applications.

Environment Variable Errors

Make sure all required environment variables are set correctly in the .env file.

Logs and Debugging
Check the logs of individual services for error messages:

bash
Copy code
docker-compose logs -f <service_name>
Use Docker's built-in tools to inspect containers and networks:

bash
Copy code
docker inspect <container_id_or_name>
docker network ls
docker network inspect <network_name>
Validate Docker Compose Configuration

Validate your docker-compose.yml file:

bash
Copy code
docker-compose config
Contributing
We welcome contributions! Please follow these steps:

Fork the Repository

Click the "Fork" button at the top right of the repository page.

Create a Feature Branch

bash
Copy code
git checkout -b feature/your-feature-name
Commit Your Changes

bash
Copy code
git commit -am 'Add some feature'
Push to the Branch

bash
Copy code
git push origin feature/your-feature-name
Create a Pull Request

Submit a pull request detailing your changes.

License
This project is licensed under the MIT License - see the LICENSE file for details.

Additional Information
Project Components
Celery: Used for task queue management and worker processes.
Docker: Containers are used to encapsulate services and ensure consistent environments.
RabbitMQ: Acts as the message broker for Celery.
Autoscaler: Dynamically scales worker containers based on queue length.
Services Overview
GAIA (Main Application): Coordinates tasks and starts the autoscaler.
Chunker: Processes data by chunking documents.
LLM (Language Learning Model): Simulates generating responses based on input data.
Vector DB: Processes data related to vector databases.
Graph DB: Processes data related to graph databases.
Prompt: Enhances prompts or input data.