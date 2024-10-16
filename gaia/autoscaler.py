import docker
from container_manager import ContainerManager

class Autoscaler:
    def __init__(self):
        self.manager = ContainerManager()
        self.containers = []

    def scale_containers(self, desired_count, image_name):
        current_count = len(self.containers)
        if current_count < desired_count:
            for _ in range(desired_count - current_count):
                container = self.manager.start_container(image_name)
                self.containers.append(container)
        elif current_count > desired_count:
            for _ in range(current_count - desired_count):
                container = self.containers.pop()
                self.manager.stop_container(container)
