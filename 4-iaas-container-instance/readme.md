### Azure Container Instance

1. Follow command from `azure-cli-create-vm-docker-engine.sh` in the Azure Cloud Shell
2. Go to the Azure Portal to the created Virtual Machine and access instance using "SSH using Azure CLI" 
3. Type in the SSH `nano Dockerfile` and copy content from the `Dockerfile` to the terminal and save it on the virtual machine
4. Type in the SSH `nano index.html` and copy content from the `index.html` to the terminal and save it on the virtual machine
5. Follow commands from `docker-cli.sh` in the SSH terminal in the Azure VM
6. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker Container on Azure Virtual Machine on port 8080
7. Follow commands from `azure-container-instance.sh` in the SSH terminal in the Azure VM
8. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker Container in the Azure Container instances on port 80
9. Delete resource groups
