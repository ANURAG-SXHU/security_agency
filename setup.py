from setuptools import setup, find_packages

setup(
    name='security_agency',
    version='0.0.1',
    description='Custom Security Agency App',
    author='Anurag Sahu',
    author_email='theanurag121@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'frappe>=15.0.0',
        'PyMuPDF==1.23.22',
        'Pillow>=10.0.0',
        'pytesseract>=0.3.10',
        'openai>=1.0.0',
        'requests>=2.31.0',
        'pandas>=2.0.0',
        'openpyxl>=3.1.0',
        'python-dateutil>=2.8.0',
    ]
)
