#!/bin/bash
if [ "$1" = "nocache" ]; then
    if [ -f "app/cache/cache.db" ]; then
        rm app/cache/cache.db
        echo "Cache deleted."
    fi
fi
cd app
uvicorn main:app --reload
