from glob import glob
from setuptools import find_packages, setup

package_name = 'ten_jobs'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'numpy'],
    zip_safe=True,
    maintainer='Yongwon Jang',
    maintainer_email='jang93042@gmail.com',
    description='10JOBs rebuild - smart home robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wall_follower = ten_jobs.nodes.wall_follower:main',
            'path_planner = ten_jobs.nodes.path_planner:main',
            'object_finder = ten_jobs.nodes.object_finder:main',
            'guard_mode = ten_jobs.nodes.guard_mode:main',
        ],
    },
)
