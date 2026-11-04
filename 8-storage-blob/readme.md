## Azure Blob Storage

> Using AWS instead? Follow the [AWS version of this task](aws/readme.md).

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

1. Issue the following commands in **the Azure Cloud Shell**

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables. The storage account name gets a random number, because it must be globally unique (3-24 lowercase letters and digits)
   ```bash
      RESOURCE_GROUP_NAME="myResourceGroupFrontend"
   ```
   ```bash
      STORAGE_ACCOUNT_NAME="mystorageaccount$RANDOM"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
      az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
   ```
   3. Create a storage account
   ```bash
      az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP_NAME --sku Standard_LRS
   ```
   4. Enable static website hosting on the storage account with names for index.html and error HTML document
   ```bash
      az storage blob service-properties update --account-name $STORAGE_ACCOUNT_NAME --static-website --index-document index.html --404-document error.html
   ```
   5. Create directory `website` and go there
   ```bash
      mkdir website && cd website
   ```
   6. Create file for `index.html` in `website` directory
   ```bash
      nano index.html
   ```
   7. Copy the following content to `index.html`
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>Hello World!</h1>
      </body>
   </html>
   ```
   8. Create file for `error.html` in `website` directory
   ```bash
      nano error.html
   ```
   9. Copy the following content to `error.html`
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>ERROR</h1>
      </body>
   </html>
   ```
   10. Upload the files from the `website` directory (the current directory) to the `$web` container
   ```bash
      az storage blob upload-batch --destination \$web --source . --account-name $STORAGE_ACCOUNT_NAME
   ```
   11. Get the static website URL
   ```bash
      az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query "primaryEndpoints.web" --output tsv
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax). The storage account name gets a random number, because it must be globally unique (3-24 lowercase letters and digits)
   ```powershell
      $RESOURCE_GROUP_NAME="myResourceGroupFrontend"
   ```
   ```powershell
      $STORAGE_ACCOUNT_NAME="mystorageaccount$(Get-Random -Maximum 99999)"
   ```
   ```powershell
      $LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```powershell
      az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
   ```
   3. Create a storage account
   ```powershell
      az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP_NAME --sku Standard_LRS
   ```
   4. Enable static website hosting on the storage account with names for index.html and error HTML document
   ```powershell
      az storage blob service-properties update --account-name $STORAGE_ACCOUNT_NAME --static-website --index-document index.html --404-document error.html
   ```
   5. Create directory `website` and go there
   ```powershell
      mkdir website; cd website
   ```
   6. Create file for `index.html` in `website` directory
   ```powershell
      nano index.html
   ```

   **Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code index.html` to open the Cloud Shell editor (GUI).
   7. Copy the following content to `index.html`
   ```powershell
   <!DOCTYPE html>
   <html>
      <body>
         <h1>Hello World!</h1>
      </body>
   </html>
   ```
   8. Create file for `error.html` in `website` directory
   ```powershell
      nano error.html
   ```

   **Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code error.html` to open the Cloud Shell editor (GUI).
   9. Copy the following content to `error.html`
   ```powershell
   <!DOCTYPE html>
   <html>
      <body>
         <h1>ERROR</h1>
      </body>
   </html>
   ```
   10. Upload the files from the `website` directory (the current directory) to the `$web` container
   ```powershell
      az storage blob upload-batch --destination `$web --source . --account-name $STORAGE_ACCOUNT_NAME
   ```
   11. Get the static website URL
   ```powershell
      az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query "primaryEndpoints.web" --output tsv
   ```
2. Proof that the website is visible: open the URL in the browser
3. Delete the `index.html` file from the blob storage

   **Bash:**
   ```bash
   az storage blob delete --account-name $STORAGE_ACCOUNT_NAME --container-name \$web --name index.html
   ```
   **PowerShell:**
   ```powershell
   az storage blob delete --account-name $STORAGE_ACCOUNT_NAME --container-name `$web --name index.html
   ```
4. Refresh the website and check that the `error.html` page (`ERROR`) is visible. Azure shows the 404 error document, because `index.html` no longer exists
5. Delete the resource group (the same command works in Bash and PowerShell)
   ```bash
   az group delete --name $RESOURCE_GROUP_NAME --yes --no-wait
   ```
