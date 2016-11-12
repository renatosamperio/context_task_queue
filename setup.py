import os
from setuptools import setup

setup(
    name = "zmicroservices",
    version = "1.0.0",
    author = "Renato Samperio",
    author_email = "renatosamperio@gmail.com",
    description = ("An alternative way for doing micro-services."),
    license = "GPL-3.0",
    keywords = "microservices zmq distributed",
    url = "https://github.com/renatosamperio/context_task_queue",
    packages=['Provider', 'Tools', 'Tools.Install', 'Tools.Templates', 'Utils', 'Services', 'Services.ContextService', 'Services.Monitor'],
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: GPL-3.0",
    ],
)