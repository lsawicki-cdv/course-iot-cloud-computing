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
4. Issue commands to the VM from the `vm.sh` script and install nginx server
5. Try to access to the VM using its public IP address via the Browser (you shouldn't have access)
6. Add inbound security rule and allow HTTP traffic (port 80) in the Network settings
7. Try again to access the VM using its public IP address via the Browser (you should have access)
8. To the same using the Azure Cloud Shell and commands from `azure-cli-create-vm.sh`
9. Delete resource groups