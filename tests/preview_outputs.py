#!/usr/bin/env python3
"""
Preview what the watcher outputs would look like for each test cycle.
This helps verify the expected behavior before computing hashes.
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
import hashlib
from pathlib import Path

# Simulate what inscriptis would extract from our test pages
EXTRACTED_CONTENT = {
    'static-article': {
        'title': 'Understanding Python Decorators',
        'description': 'A comprehensive guide to Python decorators and their use cases',
        'content': """Understanding Python Decorators

Published: January 1, 2024

Decorators are a powerful feature in Python that allow you to modify or enhance functions and classes. They provide a clean and reusable way to extend functionality.

What are Decorators?

A decorator is a function that takes another function as an argument and extends its behavior without explicitly modifying it. They are denoted by the @ symbol.

Basic Example


def my_decorator(func):
    def wrapper():
        print("Something before the function")
        func()
        print("Something after the function")
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")
        

This article remains unchanged throughout all test cycles to verify static content handling."""
    },
    'dynamic-article-1-v1': {
        'title': 'Getting Started with FastAPI',
        'description': 'Build modern APIs with Python FastAPI framework',
        'content': """Getting Started with FastAPI

Last updated: March 15, 2024

FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints.

Installation

To get started, install FastAPI and an ASGI server:

pip install fastapi uvicorn

Hello World Example


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
        

Version 1.0 - Initial release"""
    },
    'dynamic-article-1-v2': {
        'title': 'Getting Started with FastAPI',
        'description': 'Build modern APIs with Python FastAPI framework - Updated Guide',
        'content': """Getting Started with FastAPI

Last updated: March 20, 2024

FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints. It's one of the fastest Python frameworks available.

Installation

To get started, install FastAPI and an ASGI server:

pip install fastapi uvicorn[standard]

Hello World Example


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World", "framework": "FastAPI"}
        

New Feature: Automatic Documentation

FastAPI automatically generates interactive API documentation. Access it at /docs for Swagger UI or /redoc for ReDoc.

Version 2.0 - Added async support and documentation section"""
    },
    'dynamic-article-1-v3': {
        'title': 'Getting Started with FastAPI - Complete Guide',
        'description': 'Build modern APIs with Python FastAPI framework - Complete Tutorial',
        'content': """Getting Started with FastAPI - Complete Guide

Last updated: March 25, 2024

FastAPI is a modern, fast web framework for building APIs with Python 3.8+ based on standard Python type hints. It's one of the fastest Python frameworks available, with performance comparable to NodeJS and Go.

Installation

To get started, install FastAPI and an ASGI server:

pip install "fastapi[all]"

Hello World Example


from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/")
async def read_root():
    return {"Hello": "World", "framework": "FastAPI"}

@app.post("/items/")
async def create_item(item: Item):
    return {"item": item, "message": "Item created successfully"}
        

Automatic Documentation

FastAPI automatically generates interactive API documentation. Access it at /docs for Swagger UI or /redoc for ReDoc.

New: Database Integration

FastAPI works great with SQLAlchemy and async databases. Check out the official tutorial for database integration patterns.

Performance Tips

  * Use async/await for I/O operations
  * Enable response caching where appropriate
  * Use Pydantic models for validation

Version 3.0 - Added Pydantic models, database section, and performance tips"""
    },
    'dynamic-article-2-v1': {
        'title': 'Introduction to Docker Containers',
        'description': 'Learn the basics of Docker containerization',
        'content': """Introduction to Docker Containers

Published: February 10, 2024

Docker is a platform that uses containerization to make it easier to create, deploy, and run applications.

What is Docker?

Docker allows you to package an application with all of its dependencies into a standardized unit called a container.

Key Concepts

  * Images: Read-only templates used to create containers
  * Containers: Running instances of images
  * Dockerfile: Text file with instructions to build images

Basic Commands


# Pull an image
docker pull ubuntu

# Run a container
docker run -it ubuntu bash

# List containers
docker ps
        

This article remains at version 1 for the first two test cycles."""
    },
    'dynamic-article-2-v2': {
        'title': 'Introduction to Docker Containers - Extended Guide',
        'description': 'Learn the basics of Docker containerization with advanced topics',
        'content': """Introduction to Docker Containers - Extended Guide

Published: February 10, 2024 | Updated: March 25, 2024

Docker is a platform that uses containerization to make it easier to create, deploy, and run applications. It has become an essential tool in modern DevOps practices.

What is Docker?

Docker allows you to package an application with all of its dependencies into a standardized unit called a container. Containers are lightweight and portable.

Key Concepts

  * Images: Read-only templates used to create containers
  * Containers: Running instances of images
  * Dockerfile: Text file with instructions to build images
  * Docker Hub: Cloud-based registry for Docker images
  * Volumes: Persistent data storage for containers

Basic Commands


# Pull an image
docker pull ubuntu:latest

# Run a container
docker run -it --name mycontainer ubuntu bash

# List all containers
docker ps -a

# Stop a container
docker stop mycontainer

# Remove a container
docker rm mycontainer
        

Docker Compose

Docker Compose is a tool for defining and running multi-container Docker applications. Create a docker-compose.yml file:


version: '3'
services:
  web:
    image: nginx
    ports:
      - "80:80"
  db:
    image: postgres
    environment:
      POSTGRES_PASSWORD: secret
        

Best Practices

 1. Keep images small and focused
 2. Use official base images when possible
 3. Don't run containers as root
 4. Use .dockerignore files

Version 2.0 - Added Docker Compose section and best practices"""
    }
}

def generate_markdown_content(article_data, url, timestamp):
    """Generate the markdown content that watcher would create."""
    content = f"""# {article_data['title']}

**URL:** {url}  
**Fetched:** {timestamp}

---

{article_data['content']}"""
    return content

def simulate_cycle_outputs(cycle):
    """Simulate what files would be created in each cycle."""
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle} OUTPUTS")
    print(f"{'='*80}\n")
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Define what content is served in each cycle
    cycle_content = {
        1: {
            'static-article': 'static-article',
            'dynamic-article-1': 'dynamic-article-1-v1',
            'dynamic-article-2': 'dynamic-article-2-v1',
        },
        2: {
            'static-article': 'static-article',
            'dynamic-article-1': 'dynamic-article-1-v2',
            'dynamic-article-2': 'dynamic-article-2-v1',
        },
        3: {
            'static-article': 'static-article',
            'dynamic-article-1': 'dynamic-article-1-v3',
            'dynamic-article-2': 'dynamic-article-2-v2',
        }
    }
    
    # Show what would be in each markdown file
    for slug, content_key in cycle_content[cycle].items():
        article_data = EXTRACTED_CONTENT[content_key]
        url = f"http://localhost:8888/{slug}"
        
        print(f"--- content/{slug}.md ---")
        markdown = generate_markdown_content(article_data, url, timestamp)
        print(markdown[:500] + "...\n" if len(markdown) > 500 else markdown + "\n")
        
        # Calculate content hash (what watcher uses for change detection)
        text_content = article_data['content']
        content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
        print(f"Content hash: {content_hash[:16]}...")
    
    # Show changes detected
    if cycle == 1:
        print("\nChanges: All articles are new (initial scrape)")
    elif cycle == 2:
        print("\nChanges: dynamic-article-1 updated (v1 -> v2)")
    elif cycle == 3:
        print("\nChanges: dynamic-article-1 updated (v2 -> v3), dynamic-article-2 updated (v1 -> v2)")
    
    # Show git commit that would be made
    print(f"\nGit commit message:")
    if cycle == 1:
        print("Initial scrape of 3 sites")
    elif cycle == 2:
        print("Update content for 1 site")
    elif cycle == 3:
        print("Update content for 2 sites")

def main():
    print("WATCHER INTEGRATION TEST - EXPECTED OUTPUTS PREVIEW")
    print("This shows what the watcher would generate for each test cycle")
    
    for cycle in [1, 2, 3]:
        simulate_cycle_outputs(cycle)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe integration test will verify:")
    print("1. Static article never changes (same hash all 3 cycles)")
    print("2. Dynamic article 1 changes in cycles 2 and 3")
    print("3. Dynamic article 2 only changes in cycle 3")
    print("4. Git commits reflect the correct number of changes")
    print("5. All files are generated with proper format")

if __name__ == "__main__":
    main()