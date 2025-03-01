### Azure Container Instance

1. Issue the following commands in **the Azure Cloud Shell**
   1. Set the terminal environmental variables 
   ```bash
      RESOURCE_GROUP="myResourceGroupVMForDocker"
      LOCATION="uksouth"
      VM_NAME="my-vm-mqtt-docker"
      IMAGE="Ubuntu2204"
      SIZE="Standard_B1s"
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a virtual machine using the terminal environmental variables
   ```bash
      az vm create \
         --resource-group $RESOURCE_GROUP \
         --name $VM_NAME \
         --image $IMAGE \
         --size $SIZE \
         --admin-username azureuser \
         --generate-ssh-keys
   ```
   4. Install the docker engine on the virtual machine set using the terminal environmental variables
   ```bash
      az vm extension set \
         --resource-group $RESOURCE_GROUP \
         --vm-name $VM_NAME \
         --name DockerExtension \
         --publisher Microsoft.Azure.Extensions \
         --version 1.0 \
         --settings '{"docker": {"port": "2375"}}'
   ```
   5. Install the Azure CLI on the virtual machine set using the terminal environmental variables
   ```bash
      az vm extension set \
         --resource-group $RESOURCE_GROUP \
         --vm-name $VM_NAME \
         --name customScript \
         --publisher Microsoft.Azure.Extensions \
         --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/4-iaas-container-instance/install-azure-cli.sh"]}' \
         --protected-settings '{"commandToExecute": "./install-azure-cli.sh"}'
   ```
   6. Create network security group rule for the virtual machine scale using the terminal environmental variables to open the 8080 port that will be used later by the HTTP server in a Docker container 
   ```bash
      az network nsg rule create \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${VM_NAME}NSG \
         --name allow-http \
         --protocol tcp \
         --priority 1020 \
         --destination-port-range 8080 \
         --access allow
   ```
2. Access the Virtual machine using "SSH using Azure CLI" on the Azure portal
3. In the SSH of the Virtual Machine issue the following commands:
   1. Create Dockerfile 
   ```bash
      nano Dockerfile
   ```
   2. Copy the following content to the terminal and save it on the virtual machine
   ```
      ARG UBUNTU_VERSION=22.04
      FROM ubuntu:${UBUNTU_VERSION} AS base

      # OS dependencies and packages
      RUN apt-get update && \
         apt-get install nginx --no-install-recommends -y \
         && rm -rf /var/lib/apt/lists/*

      EXPOSE 80
      WORKDIR /var/www/html

      COPY index.html /var/www/html/index.html

      CMD [ "nginx", "-g", "daemon off;" ]
   ```
   3. Create HTML file
   ```bash
      nano index.html
   ```
   4. Copy the following content to the terminal and save it on the virtual machine
   ```
      <h1>Hello World from Docker!</h1>
   ```
   5. Add Docker to sudo group
   ```bash
      sudo groupadd docker
      sudo usermod -aG docker $USER
      sudo reboot
   ```
   6. Connect once again via SSH after the VM rebooted
   7. Build the Docker image from the `Dockerfile`
   ```bash
      docker build -t my-custom-app:1.0.0 .
   ```
   8. Run the Docker container with the Docker image that was build in the previous step `my-custom-app:1.0.0`
   ```bash
      docker run --rm -p 8080:80 my-custom-app:1.0.0 &
   ```
4. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker Container on Azure Virtual Machine on port 8080
5. Run the the same Docker Image using Azure Container instance. In **the SSH of the Virtual Machine** issue the following commands
   1. Set the terminal environmental variables 
   ```bash
      RESOURCE_GROUP="container-test"
      ACI_NAME="mycontainertest"
      ACI_IMAGE="my-custom-app:1.0.0"
      LOCATION="eastus"
   ```
   2. Authenticate the Azure CLI
   ```bash
      az login
   ```
   3. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   4. Create a container registry to save the Docker Image
   ```bash
     az acr create --resource-group $RESOURCE_GROUP --name $ACI_NAME --sku Basic
   ```
   5. Log in to the container registry
   ```bash
      az acr login --name $ACI_NAME
   ```
   6. Push the Docker image to the container registry
   ```bash
      docker tag $ACI_IMAGE $ACI_NAME.azurecr.io/$ACI_IMAGE
      docker push $ACI_NAME.azurecr.io/$ACI_IMAGE
   ```
   7. Check if the container image is available in the Azure portal in the container registry
   8. Create a container instance from the Docker image
   ```bash
      az acr update -n $ACI_NAME --admin-enabled true

      REGISTRY_USERNAME=$(az acr credential show --name $ACI_NAME --query username --output tsv)

      REGISTRY_PASSWORD=$(az acr credential show --name $ACI_NAME --query passwords[0].value --output tsv)
      
      az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $ACI_NAME.azurecr.io/$ACI_IMAGE --cpu 1 --memory 1 --registry-login-server $ACI_NAME.azurecr.io --registry-username $REGISTRY_USERNAME --registry-password $REGISTRY_PASSWORD --dns-name-label $ACI_NAME --ports 80 --os-type Linux
   ```
6. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker Container in the Azure Container instances on port 80
7.  Delete resource groups
