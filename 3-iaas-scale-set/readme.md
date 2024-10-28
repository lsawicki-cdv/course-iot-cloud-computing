### Azure Virtual Machine Scale Set task

1. Open the Azure Cloud Shell
2. Follow commands from `azure-cli-create-vm-scale-set.sh` in the Azure Cloud Shell
3. Try to proof that the HTTP traffic goes to both Virtual Machines (the "Hello World from" text should be different in the browser)
4. Do the same however using the Azure Portal, not the Azure CLI
   1. Create resource group if you don't have any
   2. Create Azure Virtual machine Scale Set
   3. Region: UK South
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
