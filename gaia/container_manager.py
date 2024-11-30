import docker
import logging

class ContainerManager:
    def __init__(self):
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        self.logger = logging.getLogger(__name__)

    def start_container(self, image_name, env_vars=None, command=None):
        self.logger.info(f"Starting container with image {image_name}")
        try:
            container = self.client.containers.run(
                image_name,
                detach=True,
                environment=env_vars,
                command=command,
            )
            return container
        except Exception as e:
            self.logger.error(f"Error starting container: {e}")
            raise


    def stop_container(self, container):
        self.logger.info(f"Stopping container {container.id}")
        try:
            container.stop()
            container.remove()
        except Exception as e:
            self.logger.error(f"Error stopping container: {e}")

    def get_logs(self, container):
        return container.logs().decode('utf-8')
