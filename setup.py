from setuptools import setup

name = "portugal_compliance"

setup(
    name=name,
    version="0.0.1", # Will be synced with __init__.py and pyproject.toml
    description="Compliance with Portuguese fiscal regulations (ATCUD, SAFT-PT, Digital Signatures) for ERPNext.",
    author="Manus AI (on behalf of user)",
    author_email="user@example.com", # Placeholder
    packages=["portugal_compliance"], # This should be the name of your app's module directory
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe>=15"], # Adjust based on actual Frappe/ERPNext version compatibility
    # entry_points={
    #     "frappe_applications": [
    #         "portugal_compliance = portugal_compliance.utils:get_metadata"
    #     ]
    # }
)

