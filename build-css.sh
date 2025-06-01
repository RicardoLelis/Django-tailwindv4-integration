#!/bin/bash
cd /Users/lelisra/Documents/code/tailwind4-django-how
npx @tailwindcss/cli -i ./project/static/src/styles.css -o ./project/static/dist/styles.css --content "./project/**/*.html"
echo "Tailwind CSS build complete!"