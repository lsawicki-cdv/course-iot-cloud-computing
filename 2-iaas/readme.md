### Azure Virtual Machine task

1. Create Azure Virtual Machine from Azure Portal: https://portal.azure.com/#create/Microsoft.VirtualMachine-ARM
   1. Create resource group if you don't have any
   2. Region: UK South
   3. Image: Ubuntu 22.04
   4. Size: B1s (free)
   5. Allow port 22
   6. Click "Review+Create"
   7. Wait and Click "Create"
2. Wait for resource creation
3. Access instance using "SSH using Azure CLI"
4. Issue the following commands to the VM from the `vm.sh` script and install nginx server
```bash
# Use this for your user data (script from top to bottom)
# install httpd (Linux 2 version)
sudo apt update -y
# install ngnix server
sudo apt install nginx -y
# start ngnix server
sudo systemctl start nginx
# enable ngnix server
sudo systemctl enable nginx
# change welcome page to custom page
echo "<h1>Hello World from $(hostname -f)</h1>" | sudo tee /var/www/html/index.html
```
5. Try to access to the VM using its public IP address via the Browser (you shouldn't have access)
6. Add inbound security rule and allow HTTP traffic (port 80) in the Network settings
7. Try again to access the VM using its public IP address via the Browser (you should have access)
8. Delete the resource
9. Issue the following commands in **the Azure Cloud Shell**
   1. Set the terminal environmental variables 
   ```bash
   RESOURCE_GROUP="myResourceGroupVM"
   LOCATION="uksouth"
   VM_NAME="my-vm"
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
   4. Install ngnix server on the virtual machine using the terminal environmental variables
   ```bash
      az vm extension set \
         --resource-group $RESOURCE_GROUP \
         --vm-name $VM_NAME \
         --name customScript \
         --publisher Microsoft.Azure.Extensions \
         --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh"]}' \
         --protected-settings '{"commandToExecute": "./vm.sh"}'    
   ```
   5. List the network security group rules on the virtual machine using the terminal environmental variables
   ```bash
      az network nsg rule list \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${VM_NAME}NSG \
         --output table  
   ```
   6. Create network security group rule for the virtual machine using the terminal environmental variables to open the http port (80)
   ```bash
      az network nsg rule create \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${VM_NAME}NSG \
         --name allow-http \
         --protocol tcp \
         --priority 1020 \
         --destination-port-range 80 \
         --access allow
   ```
   7. Get the public IP address of the virtual machine and save it to the terminal environmental variable `IP_ADDRESS`
   ```bash
      IP_ADDRESS=$(az vm show \
         --resource-group $RESOURCE_GROUP \
         --name $VM_NAME \
         --show-details \
         --query [publicIps] \
         --output tsv)
    ```
    8. Check connection to the HTTP server running on the virtual machine
    ```bash
      curl --connect-timeout 5 http://$IP_ADDRESS
    ```
10. Delete all resource groups