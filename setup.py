from setuptools import setup

setup(
    name='pdf-crawler',
    version='0.1',
    install_requires=[
        'beautifulsoup4',
        'click',
        'requests',
        'selenium',
        'requests_html==0.10.0',
        'psutil',
        'django',
        'whoosh',
        'pypdf4',
        'python-pptx',
        'python-docx',
        'striprtf',
        'django-haystack[whoosh]',
        'scikit-build', # 0.16.6 ok on OSX 10.9 - to build cmake then opencv (because of ocr package)
        # !!! RUN python -m pip install --only-binary=:all: numpy==1.19.5
        # !!! INSTALL Qt4 before on OSX !
        #'cmake==3.6.3', #?? works ??
        #'opencv-python==3.4.0.14',  # use CLANG 9 on OSX 10.9
        'opencv-python-headless==3.4.10.37',  # 3.4.8.29 ? use CLANG 9 >> 10 because of 1 error ! on OSX 10.9
    ],
    extras_require={
        'tests': [
            'pytest',
            'pytest-cov',
            'pytest-flakes',
            'pytest-pep8',
        ],
    },
    entry_points={
        'console_scripts': [
            'pdf-crawler = crawler:crawl',
        ],
    },
)
