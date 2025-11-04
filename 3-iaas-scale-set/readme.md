### Azure Virtual Machine Scale Set task

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

1. Open the Azure Cloud Shell (Bash)
2. Issue the following commands in **the Azure Cloud Shell (Bash)**
   1. Set the terminal environmental variables
   ```bash
      RESOURCE_GROUP="myResourceGroupScaleSet2"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   ```bash
      SCALE_SET_NAME="myScaleSet2"
   ```
   ```bash
      IMAGE="Ubuntu2204"
   ```
   ```bash
      SIZE="Standard_B1s"
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a virtual machine scale set using the terminal environmental variables
   ```bash
      az vmss create \
         --resource-group $RESOURCE_GROUP \
         --name $SCALE_SET_NAME \
         --image $IMAGE \
         --upgrade-policy-mode automatic \
         --admin-username azureuser \
         --generate-ssh-keys \
         --instance-count 2 \
         --vm-sku $SIZE
   ```
   4. Install ngnix server on the virtual machine scale set using the terminal environmental variables
   ```bash
      az vmss extension set \
         --resource-group $RESOURCE_GROUP \
         --vmss-name $SCALE_SET_NAME \
         --name customScript \
         --publisher Microsoft.Azure.Extensions \
         --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh"]}' \
         --protected-settings '{"commandToExecute": "./vm.sh"}'   
   ```
   5. List the network security group rules on the virtual machine using the terminal environmental variables
   ```bash
      az network nsg rule list \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${SCALE_SET_NAME}NSG \
         --output table
   ```
   6. Create network security group rule for the virtual machine scale set using the terminal environmental variables to open the http port (80)
   ```bash
      az network nsg rule create \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${SCALE_SET_NAME}NSG \
         --name allow-http \
         --protocol tcp \
         --priority 1020 \
         --destination-port-range 80 \
         --access allow
   ```
   7. Get the public IP address of the load balancer and save it to the terminal environmental variable `IP_ADDRESS`
   ```bash
      IP_ADDRESS=$(az network public-ip show \
         --resource-group $RESOURCE_GROUP \
         --name ${SCALE_SET_NAME}LBPublicIP \
         --query [ipAddress] \
         --output tsv)
    ```
    8. Check connection to the HTTP server running on both virtual machines
    ```bash
      curl --connect-timeout 5 http://$IP_ADDRESS
    ```
3. Try to proof that the HTTP traffic goes to both Virtual Machines (the "Hello World from" text should be different in the browser)
4. Do the same however using the Azure Portal, not the Azure CLI
   1. Create resource group if you don't have any
   2. Create Azure Virtual machine Scale Set
   3. Region: UK South (or your allowed region based on Policy)
   4. Instance count: 2
   5. Image: Ubuntu 22.04
   6. Size: B1s (free)
   7. Allow port 22
   8. Click "Review+Create"
   9. Wait and Click "Create"
   10. Go to your Azure Scale Set -> Networking -> Load balancing
   11. Add load balancer with port 80 open
   12. Add in the load balancer a backend pool to your virtual machines (Configuration for IP address). Add virtual machines to the backend pool using private IP addresses. Click Save.
   13. In the load balancer add Load Balancing rule for your backend pool for port 80
   14. Go to your Azure Scale Set -> Networking -> Network Settings
   15. Add inbound security rule for HTTP traffic (port 80)
   16. Go to each virtual machine and access instance using "SSH using Azure CLI"
   17. Issue commands to the VM from the `2-iaas/vm.sh` script and install nginx server
5. Delete resource group
