#!/usr/bin/env python3
"""
Certificate Generation Script for IoT Device

This script generates a self-signed X.509 certificate that can be used
to authenticate an IoT device with Azure IoT Hub.

In production, you should use certificates signed by a trusted Certificate Authority (CA).
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import os


def generate_device_certificate(
    device_id="my-iot-device",
    validity_days=365,
    key_size=2048
):
    """
    Generate a self-signed X.509 certificate for IoT device authentication.

    Args:
        device_id: The device identifier (will be used as Common Name)
        validity_days: How many days the certificate should be valid
        key_size: RSA key size in bits (2048 or 4096 recommended)

    Returns:
        tuple: (certificate, private_key)
    """

    print(f"Generating certificate for device: {device_id}")
    print(f"Key size: {key_size} bits")
    print(f"Validity: {validity_days} days")
    print()

    # Generate private key
    print("Generating private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    print("✓ Private key generated")

    # Create certificate subject (who the certificate identifies)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Mazowieckie"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Warsaw"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IoT Course"),
        x509.NameAttribute(NameOID.COMMON_NAME, device_id),
    ])

    # Build certificate
    print("Building certificate...")
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(issuer)  # Self-signed, so issuer = subject
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())

    # Set validity period
    now = datetime.datetime.utcnow()
    cert_builder = cert_builder.not_valid_before(now)
    cert_builder = cert_builder.not_valid_after(now + datetime.timedelta(days=validity_days))

    # Add extensions
    # Subject Alternative Name (useful for additional identities)
    cert_builder = cert_builder.add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(device_id),
        ]),
        critical=False,
    )

    # Basic constraints (this is an end-entity certificate, not a CA)
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )

    # Key usage (what the key can be used for)
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )

    # Sign the certificate with the private key (self-signed)
    certificate = cert_builder.sign(
        private_key=private_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )
    print("✓ Certificate created and self-signed")

    return certificate, private_key


def save_certificate_files(certificate, private_key, prefix="device"):
    """
    Save certificate and private key to files in various formats.

    Args:
        certificate: The X.509 certificate object
        private_key: The private key object
        prefix: Filename prefix
    """

    # Save certificate in PEM format (text, Base64 encoded)
    cert_filename = f"{prefix}-cert.pem"
    with open(cert_filename, "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))
    print(f"✓ Certificate saved to: {cert_filename}")

    # Save private key in PEM format
    key_filename = f"{prefix}-key.pem"
    with open(key_filename, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()  # No password protection
        ))
    print(f"✓ Private key saved to: {key_filename}")

    # Save as PFX/PKCS12 (combined certificate + key, used by some tools)
    pfx_filename = f"{prefix}-cert.pfx"
    pfx_data = serialization.pkcs12.serialize_key_and_certificates(
        name=b"device-cert",
        key=private_key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.NoEncryption()  # No password
    )
    with open(pfx_filename, "wb") as f:
        f.write(pfx_data)
    print(f"✓ Certificate + Key saved to: {pfx_filename}")

    print()
    print("=" * 60)
    print("IMPORTANT SECURITY NOTES:")
    print("=" * 60)
    print(f"• Keep '{key_filename}' SECRET - it's your private key!")
    print(f"• Share '{cert_filename}' - it's public and safe to share")
    print(f"• In production, use password-protected keys and secure storage")
    print(f"• This is a SELF-SIGNED certificate for TESTING only")
    print("=" * 60)

    return cert_filename, key_filename, pfx_filename


def main():
    """Main function to generate and save certificate."""

    print("=" * 60)
    print("IoT Device Certificate Generator")
    print("=" * 60)
    print()

    # You can customize these values
    device_id = "my-iot-device"
    validity_days = 365

    # Generate certificate and key
    certificate, private_key = generate_device_certificate(
        device_id=device_id,
        validity_days=validity_days
    )

    print()

    # Save to files
    save_certificate_files(certificate, private_key)

    print()
    print("Next steps:")
    print("1. Run 'python inspect_certificate.py' to view certificate details")
    print("2. Upload 'device-cert.pem' to Azure IoT Hub")
    print("3. Create a device in IoT Hub with X.509 authentication")
    print("4. Update and run 'device_simulator_x509.py'")
    print()


if __name__ == "__main__":
    main()
