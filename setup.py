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
        
        
        # FOR OPEN CV

        #'scikit-build', # 0.16.6 ok on OSX 10.9 - to build cmake then opencv (because of ocr package)
        # !!! RUN python -m pip install --only-binary=:all: numpy==1.19.5
        # !!! RUN python -m pip install --only-binary=:all: cmake==3.25.3
        # !!! RUN python -m pip install --only-binary=:all: scipy
        
        # !!! INSTALL Qt4 before on OSX if installing opencv-python (NOT for -headless)
        # use CLANG 14 on OSX 10.9 WITH :
        # export LDFLAGS="-mlinker-version=274.2"
        # export CCFLAGS="-mlinker-version=274.2"
        # export CFLAGS="-mlinker-version=274.2"
        #'opencv-python==3.4.0.14', 
        # OR
        #'opencv-python-headless==3.4.10.37', # use 3.4.8.29 on ALWAYSDATA #  use CLANG 9 ! (1 error though) on OSX 10.9
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
