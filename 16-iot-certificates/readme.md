## Azure IoT Hub - X.509 Certificates and TLS

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. If you need to create a new IoT Hub for this exercise, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead of UK South if necessary.

### Learning Objectives
- Understand TLS (Transport Layer Security) and how it secures IoT communications
- Learn about X.509 certificates and the Chain of Trust concept
- Create and inspect digital certificates
- Authenticate IoT devices using X.509 certificates instead of symmetric keys
- Understand the difference between self-signed and CA-signed certificates

### Tested environments
Ubuntu 22.04
Python 3.10.12

### Background

#### What is TLS?
Transport Layer Security (TLS) is a cryptographic protocol that provides secure communication over networks. When your IoT device connects to Azure IoT Hub, TLS ensures:
- **Encryption**: Data is encrypted so it cannot be read by attackers
- **Authentication**: You can verify the identity of the server (and optionally the client)
- **Integrity**: Data cannot be tampered with during transmission

#### What are X.509 Certificates?
X.509 certificates are digital documents that prove identity. They contain:
- **Public Key**: Used for encryption
- **Identity Information**: Subject name, organization, etc.
- **Digital Signature**: Proves the certificate is authentic
- **Issuer Information**: Who issued/signed this certificate

#### Chain of Trust
Certificates form a chain:
1. **Root Certificate**: Self-signed, trusted by default (installed in OS/browser)
2. **Intermediate Certificate**: Signed by root, signs other certificates
3. **End-entity Certificate**: Your device certificate, signed by intermediate or root

This chain allows you to trust a certificate if you trust the root that signed it.

### Exercise

In this exercise, you will:
1. Create a self-signed certificate for testing
2. Inspect certificate properties to understand their structure
3. Register the certificate with Azure IoT Hub
4. Connect an IoT device using X.509 authentication instead of connection strings

#### Prerequisites
1. Azure account with an IoT Hub (you can create one manually or use exercise 13/15)
2. Python 3.10+ installed
3. OpenSSL installed (usually pre-installed on Linux/macOS)

### Steps

#### 1. Setup Python Environment

On **macOS/Linux**:
```bash
cd 16-iot-certificates
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On **Windows**:
```powershell
cd 16-iot-certificates
py -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

#### 2. Generate Self-Signed Certificate

Run the certificate generation script:
```bash
python generate_certificate.py
```

This creates:
- `device-cert.pem`: Your device certificate (public)
- `device-key.pem`: Your device private key (keep secret!)
- `device-cert.pfx`: Combined certificate and key (for Windows/other tools)

**Important**: In production, certificates should be signed by a trusted Certificate Authority (CA). Self-signed certificates are for testing only.

#### 3. Inspect the Certificate

Learn what's inside a certificate:
```bash
python inspect_certificate.py
```

This script shows you:
- Subject (who the certificate identifies)
- Issuer (who signed the certificate)
- Validity period (when it expires)
- Public key information
- Certificate fingerprint (unique identifier)

#### 4. Register Certificate with IoT Hub

1. Go to Azure Portal → Your IoT Hub
2. Navigate to **Security settings** → **Certificates**
3. Click **+ Add** to add a new certificate
4. Upload `device-cert.pem`
5. Give it a name like "device-test-cert"
6. You don't need to verify it for self-signed certificates in testing

#### 5. Create IoT Device with X.509 Authentication

1. In Azure Portal, go to your IoT Hub → **Device management** → **Devices**
2. Click **+ Add Device**
3. Set:
   - **Device ID**: `device-x509-test` (or any name)
   - **Authentication type**: Select **X.509 Self-Signed**
   - **Primary Thumbprint**: Copy from the output of `inspect_certificate.py` (the SHA-1 fingerprint)
   - **Secondary Thumbprint**: Copy from the output of `inspect_certificate.py` (the SHA-1 fingerprint)
4. Click **Save**

#### 6. Configure and Run the Device Simulator

Edit `device_simulator_x509.py` and update these variables:
```python
IOTHUB_HOSTNAME = "your-hub-name.azure-devices.net"  # Your IoT Hub hostname
DEVICE_ID = "device-x509-test"  # The device ID you created
```

Run the simulator:
```bash
python device_simulator_x509.py
```

The device will:
- Load the certificate and private key
- Establish a TLS connection to IoT Hub
- Authenticate using the X.509 certificate (no connection string needed!)
- Send temperature and humidity telemetry

#### 7. Verify Messages in Azure

1. Go to Azure Portal → Your IoT Hub → **Overview**
2. Scroll down to see the metrics
3. You should see "Device to cloud messages" increasing
4. If you set up message routing (like in exercise 13), check your storage account

#### 8. Understand the TLS Handshake

When your device connects, here's what happens:
1. **Client Hello**: Device says "I want to connect with TLS"
2. **Server Hello**: IoT Hub responds with its certificate
3. **Certificate Verification**: Device verifies IoT Hub's certificate chain
4. **Client Certificate**: Device sends its certificate (`device-cert.pem`)
5. **Certificate Verification**: IoT Hub verifies device certificate
6. **Key Exchange**: Both parties establish encryption keys
7. **Secure Connection**: All data is now encrypted

Try running with verbose logging to see this:
```bash
python device_simulator_x509.py --verbose
```

### Questions to Consider

1. **Why is X.509 more secure than symmetric keys?**
   - Private key never transmitted over network
   - Can use hardware security modules (HSM) to protect keys
   - Can revoke certificates without changing device firmware

2. **What happens if certificate expires?**
   - Device cannot authenticate
   - Certificate must be renewed before expiry
   - Good practice: Monitor expiry dates

3. **What is the thumbprint/fingerprint?**
   - Hash (SHA-1 or SHA-256) of the certificate
   - Unique identifier
   - Used by IoT Hub to match device to certificate

4. **Self-signed vs CA-signed certificates?**
   - Self-signed: Easy for testing, but you must manually trust each one
   - CA-signed: IoT Hub trusts the CA, automatically trusts all certificates it signs
   - Production systems should use CA-signed certificates

### Cleanup

When finished:
```bash
# Delete the certificate files if you want
rm device-cert.pem device-key.pem device-cert.pfx

# Deactivate virtual environment
deactivate

# Delete the IoT device from Azure Portal to avoid any potential charges
```

### Additional Resources

- [X.509 Certificate Authentication in IoT Hub](https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-x509ca-overview)
- [TLS Protocol Overview](https://en.wikipedia.org/wiki/Transport_Layer_Security)
- [Azure IoT Hub Security](https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-security)

### Troubleshooting

**"Certificate verification failed"**
- Ensure the thumbprint matches exactly
- Check that you uploaded the correct .pem file to IoT Hub
- Verify the device ID matches

**"Connection refused"**
- Check IoT Hub hostname is correct
- Ensure device exists in IoT Hub
- Verify network connectivity

**"Certificate expired"**
- Generate a new certificate with longer validity
- Update thumbprint in IoT Hub device settings
