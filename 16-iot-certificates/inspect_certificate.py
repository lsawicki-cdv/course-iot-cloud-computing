#!/usr/bin/env python3
"""
Certificate Inspection Script

This script reads and displays information from an X.509 certificate file.
Use it to understand the structure and contents of certificates.
"""

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import sys
import os


def load_certificate(filename):
    """
    Load an X.509 certificate from a PEM file.

    Args:
        filename: Path to the .pem certificate file

    Returns:
        Certificate object
    """
    try:
        with open(filename, "rb") as f:
            cert_data = f.read()
            certificate = x509.load_pem_x509_certificate(cert_data, default_backend())
        return certificate
    except FileNotFoundError:
        print(f"Error: Certificate file '{filename}' not found!")
        print("Run 'python generate_certificate.py' first to create a certificate.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading certificate: {e}")
        sys.exit(1)


def print_certificate_info(certificate):
    """
    Display detailed information about a certificate.

    Args:
        certificate: The X.509 certificate object
    """

    print("=" * 70)
    print("CERTIFICATE INFORMATION")
    print("=" * 70)
    print()

    # Subject - Who this certificate identifies
    print("SUBJECT (Who this certificate identifies):")
    print("-" * 70)
    subject = certificate.subject
    for attribute in subject:
        print(f"  {attribute.oid._name}: {attribute.value}")
    print()

    # Issuer - Who signed/issued this certificate
    print("ISSUER (Who signed this certificate):")
    print("-" * 70)
    issuer = certificate.issuer
    for attribute in issuer:
        print(f"  {attribute.oid._name}: {attribute.value}")

    # Check if self-signed
    if subject == issuer:
        print("  ⚠ This is a SELF-SIGNED certificate (Subject = Issuer)")
    print()

    # Serial Number - Unique identifier from issuer
    print("SERIAL NUMBER:")
    print("-" * 70)
    print(f"  {certificate.serial_number}")
    print()

    # Validity Period
    print("VALIDITY PERIOD:")
    print("-" * 70)
    print(f"  Not Before: {certificate.not_valid_before}")
    print(f"  Not After:  {certificate.not_valid_after}")

    # Check if expired
    from datetime import datetime
    now = datetime.utcnow()
    if now < certificate.not_valid_before:
        print(f"  ⚠ Certificate is NOT YET VALID")
    elif now > certificate.not_valid_after:
        print(f"  ⚠ Certificate has EXPIRED")
    else:
        days_remaining = (certificate.not_valid_after - now).days
        print(f"  ✓ Certificate is valid ({days_remaining} days remaining)")
    print()

    # Public Key Information
    print("PUBLIC KEY:")
    print("-" * 70)
    public_key = certificate.public_key()
    from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa

    if isinstance(public_key, rsa.RSAPublicKey):
        print(f"  Algorithm: RSA")
        print(f"  Key Size: {public_key.key_size} bits")
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        print(f"  Algorithm: Elliptic Curve (EC)")
        print(f"  Curve: {public_key.curve.name}")
    else:
        print(f"  Algorithm: {type(public_key).__name__}")
    print()

    # Signature Algorithm
    print("SIGNATURE ALGORITHM:")
    print("-" * 70)
    print(f"  {certificate.signature_algorithm_oid._name}")
    print()

    # Fingerprints (unique identifiers)
    print("FINGERPRINTS (Unique identifiers):")
    print("-" * 70)

    # SHA-256 fingerprint (modern, recommended)
    sha256_fingerprint = certificate.fingerprint(hashes.SHA256())
    print(f"  SHA-256: {sha256_fingerprint.hex(':').upper()}")

    # SHA-1 fingerprint (legacy, but Azure IoT Hub uses this as "thumbprint")
    sha1_fingerprint = certificate.fingerprint(hashes.SHA1())
    print(f"  SHA-1:   {sha1_fingerprint.hex(':').upper()}")
    print()
    print("  ⚠ For Azure IoT Hub, use the SHA-1 fingerprint as the 'Primary Thumbprint'")
    print()

    # Extensions
    print("CERTIFICATE EXTENSIONS:")
    print("-" * 70)
    try:
        for extension in certificate.extensions:
            print(f"  • {extension.oid._name}:")

            # Print extension details based on type
            if extension.oid._name == "subjectAlternativeName":
                for name in extension.value:
                    print(f"      {type(name).__name__}: {name.value}")

            elif extension.oid._name == "basicConstraints":
                bc = extension.value
                print(f"      CA: {bc.ca}")
                if bc.path_length is not None:
                    print(f"      Path Length: {bc.path_length}")

            elif extension.oid._name == "keyUsage":
                ku = extension.value
                usages = []
                if ku.digital_signature: usages.append("Digital Signature")
                if ku.key_encipherment: usages.append("Key Encipherment")
                if ku.content_commitment: usages.append("Content Commitment")
                if ku.data_encipherment: usages.append("Data Encipherment")
                if ku.key_agreement: usages.append("Key Agreement")
                if ku.key_cert_sign: usages.append("Certificate Signing")
                if ku.crl_sign: usages.append("CRL Signing")
                print(f"      {', '.join(usages)}")

            else:
                # Generic display for other extensions
                print(f"      {extension.value}")

            if extension.critical:
                print(f"      (CRITICAL)")
    except x509.ExtensionNotFound:
        print("  No extensions")

    print()
    print("=" * 70)


def main():
    """Main function to inspect certificate."""

    cert_filename = "device-cert.pem"

    print()
    print("=" * 70)
    print("Certificate Inspector")
    print("=" * 70)
    print()

    if not os.path.exists(cert_filename):
        print(f"Certificate file '{cert_filename}' not found.")
        print()
        print("Please run 'python generate_certificate.py' first to create a certificate.")
        print()
        return

    print(f"Loading certificate from: {cert_filename}")
    print()

    # Load and display certificate
    certificate = load_certificate(cert_filename)
    print_certificate_info(certificate)

    # Save thumbprint to file for easy reference
    sha1_fingerprint = certificate.fingerprint(hashes.SHA1())
    thumbprint = sha1_fingerprint.hex('').upper()  # No colons, uppercase

    with open("thumbprint.txt", "w") as f:
        f.write(thumbprint)

    print()
    print(f"✓ SHA-1 thumbprint saved to 'thumbprint.txt'")
    print(f"  Copy this value to Azure IoT Hub when creating the device:")
    print(f"  {thumbprint}")
    print()


if __name__ == "__main__":
    main()
