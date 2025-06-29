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
    install_requires=['frappe>=15.0.0']
)
