## AWS IoT Core - X.509 Certificates and TLS

This is the AWS version of the [Azure IoT Hub exercise](../readme.md). You will create your own self-signed X.509 certificate, register it in AWS IoT Core **without a CA**, and connect a simulated device with it. Unlike exercises 6, 13 and 15 on AWS, where AWS created the certificate and the private key for you, here the private key is generated on your computer and never leaves it: only the public certificate is uploaded.

| Azure | AWS |
|-------|-----|
| IoT Hub (existing, from exercise 13/15) | AWS IoT Core: one endpoint per account and region, nothing to create |
| Upload the certificate in IoT Hub → Certificates | `aws iot register-certificate-without-ca --status ACTIVE` |
| Device with "X.509 Self-Signed" and SHA-1 thumbprints | Thing + IoT policy, attached to the registered certificate |
| SHA-1 thumbprint identifies the certificate | SHA-256 fingerprint = certificate ID (`inspect_certificate.py` prints it in ID form) |
| `azure-iot-device` SDK | `paho-mqtt` with a TLS client certificate and `AmazonRootCA1.pem` |
| Hub "Overview" metrics | MQTT test client in the AWS Console, subscribed to `devices/+/messages/events/` |
| Clean-up of the device in the portal | CLI clean-up: detach, deactivate, delete certificate, thing and policy |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. If your account is limited to other regions (for example by your organization or a new AWS account with a selected Region), set `REGION` to the region you can use, in Step 4 and in the Cleanup. AWS IoT Core is Free Tier eligible (on accounts created before July 2025: 500,000 messages per month for 12 months; on newer accounts the costs are paid from your Free Tier credits). The simulator sends 10 messages, which costs nothing measurable. Nothing else in this exercise is billed, but delete the resources at the end (see Cleanup).

### Learning Objectives
- Understand TLS (Transport Layer Security) and how it secures IoT communications
- Learn about X.509 certificates and the Chain of Trust concept
- Create and inspect digital certificates
- Register your own certificate in AWS IoT Core and authenticate an IoT device with it instead of a certificate created by AWS
- Understand the difference between self-signed and CA-signed certificates
- Understand why a certificate registered without a CA needs SNI

### Tested environments
- Ubuntu 26.04
- Python 3.10+ (`cryptography` 41.0.7, `paho-mqtt` 1.6.1)
- AWS IoT Core (live test in eu-north-1; the readme default is eu-west-2)

### Background

#### What is TLS?
Transport Layer Security (TLS) is a cryptographic protocol that provides secure communication over networks. When your IoT device connects to AWS IoT Core, TLS ensures:
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

This chain allows you to trust a certificate if you trust the root that signed it. Your device trusts the IoT Core server because its certificate chains up to **Amazon Root CA 1** (the `AmazonRootCA1.pem` file next to the simulator). IoT Core trusts your device because you registered its certificate.

#### Certificates without a CA and SNI
AWS IoT Core can register a certificate in two ways: signed by a CA that you registered first, or on its own, **without a CA**. Your self-signed certificate is the second case. IoT Core finds such a certificate by the endpoint name that the client sends during the TLS handshake in the **SNI** (Server Name Indication) extension. A client that connects by hostname, like `paho-mqtt` in the simulator, sends it automatically. Certificates registered without a CA have the mode `SNI_ONLY` for this reason.

### Exercise

In this exercise, you will:
1. Create a self-signed certificate for testing
2. Inspect certificate properties to understand their structure
3. Register the certificate with AWS IoT Core
4. Connect an IoT device using X.509 authentication with your own certificate

#### Prerequisites
1. An AWS account (see [Exercise 1 on AWS](../../1-cloud-account/aws/readme.md)) and access to AWS CloudShell (or a local AWS CLI)
2. Python 3.10+ installed
3. OpenSSL installed (usually pre-installed on Linux/macOS; on Windows it comes with Git for Windows)

#### Where each step runs
- **On your computer**: the Python scripts, the simulator and `openssl`, because they need the private key (Steps 1-3, 6 and 8).
- **In AWS CloudShell** (or a local AWS CLI): the `aws` commands (Steps 4 and 5, and Cleanup). Upload **only** `device-cert.pem` to CloudShell. **Never upload `device-key.pem`**: the private key must stay on your computer.

### Steps

#### 1. Setup Python Environment

Open a terminal on your computer. On **macOS/Linux**:
```bash
cd 16-iot-certificates/aws
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On **Windows**:
```powershell
cd 16-iot-certificates\aws
py -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

#### 2. Generate Self-Signed Certificate

Run the shared certificate generation script (it lives one folder up, the files are created in `aws/`):
```bash
python ../generate_certificate.py
```

This creates:
- `device-cert.pem`: Your device certificate (public)
- `device-key.pem`: Your device private key (keep secret!)
- `device-cert.pfx`: Combined certificate and key (for Windows/other tools)
- `thumbprint.txt`: The SHA-1 thumbprint (only Azure IoT Hub uses it)

**Important**: In production, certificates should be signed by a trusted Certificate Authority (CA). Self-signed certificates are for testing only. The `.gitignore` files of this exercise keep the certificate, key and `.pfx` out of git: don't commit them.

#### 3. Inspect the Certificate

Learn what's inside a certificate:
```bash
python ../inspect_certificate.py
```

This script shows you:
- Subject (who the certificate identifies)
- Issuer (who signed the certificate)
- Validity period (when it expires)
- Public key information
- Certificate fingerprints (unique identifiers)

Find the line "For AWS IoT Core, the certificate ID is the SHA-256 fingerprint in lowercase without colons" and **copy the 64-character value below it**: this is the ID that AWS IoT Core will give your certificate. You will compare it in the next step.

#### 4. Register the Certificate in AWS IoT Core

Open **AWS CloudShell** (the terminal icon in the AWS Console's top bar) in the region you use. Upload the certificate: click **"Actions"** → **"Upload file"** and select `device-cert.pem` from the `16-iot-certificates/aws` folder. **Upload only the certificate, not the private key.**

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```bash
REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```bash
THING_NAME="device-x509-test"
```

Save your AWS account ID (used in the policy):
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register the certificate without a CA and save its ARN:**
```bash
CERTIFICATE_ARN=$(aws iot register-certificate-without-ca \
  --region $REGION \
  --certificate-pem file://device-cert.pem \
  --status ACTIVE \
  --query certificateArn \
  --output text)
```

**Show the registered certificate:**
```bash
CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
aws iot describe-certificate \
  --region $REGION \
  --certificate-id $CERTIFICATE_ID \
  --query "certificateDescription.[certificateId,status,certificateMode]"
```

The output shows three values:
- the certificate ID: the same 64 characters that `inspect_certificate.py` printed in Step 3,
- the status `ACTIVE`,
- the mode `SNI_ONLY`: IoT Core accepts this certificate only when the device sends the endpoint name in SNI.

**Option B: Using PowerShell**

Start PowerShell in AWS CloudShell by typing `pwsh`.

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```powershell
$REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```powershell
$THING_NAME="device-x509-test"
```

Save your AWS account ID (used in the policy):
```powershell
$ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register the certificate without a CA and save its ARN:**
```powershell
$CERTIFICATE_ARN=$(aws iot register-certificate-without-ca `
  --region $REGION `
  --certificate-pem file://device-cert.pem `
  --status ACTIVE `
  --query certificateArn `
  --output text)
```

**Show the registered certificate:**
```powershell
$CERTIFICATE_ID=$CERTIFICATE_ARN.Split('/')[-1]
aws iot describe-certificate `
  --region $REGION `
  --certificate-id $CERTIFICATE_ID `
  --query "certificateDescription.[certificateId,status,certificateMode]"
```

The output shows the same three values as in Option A: the certificate ID (equal to the one from Step 3), the status `ACTIVE` and the mode `SNI_ONLY`.

#### 5. Create the Thing and the IoT Policy

Stay in AWS CloudShell, in the session where you set the variables.

**Option A: Using Bash (recommended)**

**Create the thing (the device identity in IoT Core):**
```bash
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**
```bash
cat > device-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:topic/devices/$THING_NAME/*"}
  ]
}
EOF
```
```bash
aws iot create-policy \
  --region $REGION \
  --policy-name ${THING_NAME}-policy \
  --policy-document file://device-policy.json
```

The policy is the minimum the simulator needs: it can connect only as `device-x509-test` and publish only below `devices/device-x509-test/`. Don't replace it with `iot:*` on `*` to "make it work": if the connection fails, see Troubleshooting.

**Attach the policy to the certificate, and the certificate to the thing:**
```bash
aws iot attach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
```
```bash
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**
```bash
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** from the output - you'll need it in the next step!

**Option B: Using PowerShell**

**Create the thing (the device identity in IoT Core):**
```powershell
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**
```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:topic/devices/$THING_NAME/*"}
  ]
}
"@ | Set-Content device-policy.json
```
```powershell
aws iot create-policy `
  --region $REGION `
  --policy-name "$THING_NAME-policy" `
  --policy-document file://device-policy.json
```

**Attach the policy to the certificate, and the certificate to the thing:**
```powershell
aws iot attach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
```
```powershell
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**
```powershell
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** from the output - you'll need it in the next step!

#### 6. Configure and Run the Device Simulator

Go back to the terminal on your computer, in the `16-iot-certificates/aws` folder with the virtual environment active.

Edit `device_simulator_x509.py` and update these variables:
```python
IOT_ENDPOINT = "your-endpoint-ats.iot.eu-west-2.amazonaws.com"  # The endpoint from Step 5
THING_NAME = "device-x509-test"  # The thing name you created
```

Before you run the simulator, open the **AWS Console** → **IoT Core** → **MQTT test client** → **Subscribe to a topic**, enter the topic filter `devices/+/messages/events/` and click **Subscribe**. Use the same region as in the commands above.

Run the simulator:
```bash
python device_simulator_x509.py
```

The device will:
- Load the certificate and private key
- Verify the IoT Core server certificate with `AmazonRootCA1.pem`
- Establish a TLS connection to IoT Core, sending the endpoint name as SNI
- Authenticate using the X.509 certificate (no username or password needed!)
- Send 10 temperature and humidity messages, one every 5 seconds, and print an acknowledgement for each one

**Note:** Don't commit the endpoint you typed into the simulator.

#### 7. Verify Messages in AWS

1. Look at the MQTT test client: you should see 10 messages on the topic `devices/device-x509-test/messages/events/`
2. Expand a message to see the JSON telemetry (`deviceId`, `temperature`, `humidity`, `timestamp`)
3. In the terminal, every message is followed by "Message acknowledged by IoT Core"

#### 8. Understand the TLS Handshake

When your device connects, here's what happens:
1. **Client Hello**: Device says "I want to connect with TLS" and sends the endpoint name in SNI
2. **Server Hello**: IoT Core responds with its certificate
3. **Certificate Verification**: Device verifies the IoT Core certificate chain up to Amazon Root CA 1
4. **Client Certificate**: Device sends its certificate (`device-cert.pem`)
5. **Certificate Verification**: IoT Core looks the certificate up (by the SNI endpoint, as it was registered without a CA) and checks that it is registered and `ACTIVE`
6. **Key Exchange**: Both parties establish encryption keys; the device proves it owns the private key
7. **Secure Connection**: All data is now encrypted

You can watch the handshake with `openssl s_client`. Run it on your computer, in the `16-iot-certificates/aws` folder, because it uses the private key. Replace `<endpoint>` with the endpoint from Step 5. `< /dev/null` (Bash) ends the connection at once; in PowerShell press `Ctrl+C` to stop it.

OpenSSL is pre-installed on Linux and macOS. On Windows use the one that comes with Git for Windows: run the Bash variant in **Git Bash**, where `openssl` is on the PATH, or use the PowerShell variant with the full path.

**Option A: Using Bash (recommended)**
```bash
openssl s_client \
  -connect <endpoint>:8883 \
  -servername <endpoint> \
  -cert device-cert.pem \
  -key device-key.pem \
  -CAfile AmazonRootCA1.pem < /dev/null
```

**Option B: Using PowerShell**
```powershell
& "C:\Program Files\Git\usr\bin\openssl.exe" s_client `
  -connect <endpoint>:8883 `
  -servername <endpoint> `
  -cert device-cert.pem `
  -key device-key.pem `
  -CAfile AmazonRootCA1.pem
```
(On Linux or macOS with PowerShell, use `openssl` instead of the full path.)

In the output you should see:
- the server certificate chain: depth=2 Amazon Root CA 1, depth=1 an Amazon RSA 2048 intermediate (for example `Amazon RSA 2048 M01`; the number can differ), depth=0 `*.iot.<region>.amazonaws.com`,
- the server asking for a client certificate, shown as `No client certificate CA names sent` (IoT Core does not list accepted CAs) followed by `Requested Signature Algorithms`,
- `Verify return code: 0 (ok)`.

`-servername <endpoint>` sends the endpoint name in SNI, which IoT Core uses to find a certificate registered without a CA. The simulator sends it automatically because it connects by hostname, so always use the `-ats` endpoint hostname, not an IP address.

### Questions to Consider

1. **Why is X.509 more secure than symmetric keys?**
   - Private key never transmitted over network
   - Can use hardware security modules (HSM) to protect keys
   - Can revoke certificates without changing device firmware (in IoT Core: deactivate or delete the certificate)

2. **What happens if certificate expires?**
   - Device cannot authenticate
   - Certificate must be renewed (generated, registered and attached again) before expiry
   - Good practice: Monitor expiry dates

3. **What is the thumbprint/fingerprint?**
   - Hash (SHA-1 or SHA-256) of the certificate
   - Unique identifier
   - Azure IoT Hub uses the SHA-1 thumbprint to match a device to a certificate; AWS IoT Core uses the SHA-256 fingerprint as the certificate ID

4. **Self-signed vs CA-signed certificates?**
   - Self-signed: Easy for testing, but you must register each one yourself (`register-certificate-without-ca`), and there is no CA that could revoke it: you can only deactivate it in IoT Core
   - CA-signed: you register your CA once (`register-ca-certificate`), and IoT Core trusts every certificate it signs. With just-in-time registration (JITR), a new device certificate is registered automatically when the device first connects. We only describe this here, we don't do it
   - Production systems should use CA-signed certificates

5. **Your own certificate or `create-keys-and-certificate`?**
   - With `create-keys-and-certificate` (exercises 6, 13 and 15 on AWS) AWS generates the key pair and you download the private key once
   - With your own certificate the private key is created on the device and never leaves it, which is closer to production practice (a device can even generate the key inside a secure element)

### Cleanup

When finished, run these commands in **AWS CloudShell**, in the session where you set the variables (`REGION`, `THING_NAME`, `CERTIFICATE_ARN`, `CERTIFICATE_ID`). The order matters: IoT Core refuses to delete a certificate that is still active or attached.

If your CloudShell session timed out, set the variables again:

**Option A: Using Bash (recommended)**
```bash
REGION="eu-west-2"
THING_NAME="device-x509-test"
CERTIFICATE_ARN=$(aws iot list-thing-principals --region $REGION --thing-name $THING_NAME --query "principals[0]" --output text)
CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
```

Then delete the resources:
```bash
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
aws iot detach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
aws iot delete-thing --region $REGION --thing-name $THING_NAME
aws iot delete-policy --region $REGION --policy-name ${THING_NAME}-policy
```

**Option B: Using PowerShell**
```powershell
$REGION="eu-west-2"
$THING_NAME="device-x509-test"
$CERTIFICATE_ARN=$(aws iot list-thing-principals --region $REGION --thing-name $THING_NAME --query "principals[0]" --output text)
$CERTIFICATE_ID=$CERTIFICATE_ARN.Split('/')[-1]
```

Then delete the resources:
```powershell
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
aws iot detach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
aws iot delete-thing --region $REGION --thing-name $THING_NAME
aws iot delete-policy --region $REGION --policy-name "$THING_NAME-policy"
```

Check that nothing is left:
```bash
aws iot list-things --region $REGION --query "things[].thingName"
aws iot list-certificates --region $REGION --query "certificates[].certificateId"
aws iot list-policies --region $REGION --query "policies[].policyName"
```

Then delete the local files and deactivate the virtual environment on your computer:
```bash
# The private key is the device's identity: delete it when you no longer need it
rm device-cert.pem device-key.pem device-cert.pfx thumbprint.txt

# Deactivate virtual environment
deactivate
```
(On Windows use `Remove-Item device-cert.pem, device-key.pem, device-cert.pfx, thumbprint.txt`.) Also delete `device-cert.pem` and `device-policy.json` from your CloudShell home folder, and put the placeholder back in `IOT_ENDPOINT` if you changed it.

### Additional Resources

- [Register a client certificate without a CA](https://docs.aws.amazon.com/iot/latest/developerguide/manual-cert-registration.html)
- [Transport security in AWS IoT Core (including SNI)](https://docs.aws.amazon.com/iot/latest/developerguide/transport-security.html)
- [AWS IoT Core policies](https://docs.aws.amazon.com/iot/latest/developerguide/iot-policies.html)
- [Amazon Root CA 1 (official download, to compare with `AmazonRootCA1.pem`)](https://www.amazontrust.com/repository/AmazonRootCA1.pem)
- [TLS Protocol Overview](https://en.wikipedia.org/wiki/Transport_Layer_Security)

### Troubleshooting

**"ResourceAlreadyExistsException" when registering the certificate**
- A certificate with the same content is already registered in this account and region (for example from an earlier run)
- Delete it as in Cleanup, or generate a new certificate with `python ../generate_certificate.py`

**Connection closed right after TLS, or "Message not acknowledged"**
- Check that the policy is attached to the certificate and the certificate to the thing (Step 5)
- The client ID must equal the thing name and the name in the policy (`device-x509-test`); don't widen the policy, fix the name
- Check that `THING_NAME` in the simulator matches the thing you created

**Certificate is not active**
- Run `aws iot describe-certificate` (Step 4) and check that the status is `ACTIVE`
- Activate it with `aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status ACTIVE`

**Wrong region or endpoint**
- The certificate, the thing, the policy and the endpoint must be in the same region
- Compare `REGION` with the region of the MQTT test client and the endpoint (`<id>-ats.iot.<region>.amazonaws.com`)

**SNI missing, device is not authenticated**
- Certificates registered without a CA work only when the device connects by the `iot:Data-ATS` endpoint **hostname**, not by IP address
- Use the endpoint from `--endpoint-type iot:Data-ATS` (`-ats` in the name)

**"Certificate expired"**
- Generate a new certificate (the generator makes them valid for 365 days), register it and attach it again
- Delete the old certificate as in Cleanup

**"certificate verify failed" in the simulator**
- `AmazonRootCA1.pem` is missing or changed: restore it from the repository or download it from the official link above
