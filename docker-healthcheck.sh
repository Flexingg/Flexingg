#!/bin/bash
# Simple health check for Django app
curl -f http://localhost:8000/ || exit 1