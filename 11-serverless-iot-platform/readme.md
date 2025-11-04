# Serverless IoT Platform

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Exercise

### Please create the following Azure Services using the instructions placed in this directory `11-serverless-iot-platform`
   - Azure Functions
   - Azure Cosmos DB
   - Azure Stream Analytics
   - Azure Iot Hub
### The REST API deployed using the Azure Functions should have the following endpoints. Please use [Postman](https://postman.com/) for testing

#### 1. Devices

**Request:**
- Method: `GET`
- URL: `https://<your-azure-function-name>.azurewebsites.net/api/device`
- Query Parameters:
	- `device_id` : `<some-device-id>`

**Tests:**
- Status code should be 200

#### 2. Houses

**Request:**
- Method: `POST`
- URL: `https://<your-azure-function-name>.azurewebsites.net/api/house`
- Body:
	```json
	{
			"id": "<some-id>",
			"name": "<some-house-name>",
			"location": "<location-name>"
	}
	```

#### 3. Rooms (Create)

**Request:**
- Method: `POST`
- URL: `https://<your-azure-function-name>.azurewebsites.net/api/rooms`
- Body:
	```json
	{
			"id": "<some-id>",
			"room_name": "<some-room-name>",
			"house_id": "<some-house-id>",
			"location": "<some-location-name>"
	}
	```

#### 4. GetHouse

**Request:**
- Method: `GET`
- URL: `https://<your-azure-function-name>.azurewebsites.net/api/house`
- Query Parameters:
	- `house_id`: `<some-house-id>`

#### 5. Rooms (Get)

**Request:**
- Method: `GET`
- URL: `https://<your-azure-function-name>.azurewebsites.net/api/rooms`
- Query Parameters:
	- `room_id`: `<some-room-id>` 
