from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in portugal_compliance/__init__.py
from portugal_compliance import __version__ as version

setup(
	name="portugal_compliance",
	version=version,
	description="Frappe App for Portuguese Fiscal Compliance (SAF-T, ATCUD, QR Code, Digital Signature)",
	author="Manus AI Agent",
	author_email="noreply@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
