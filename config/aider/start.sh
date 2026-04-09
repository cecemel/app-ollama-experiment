#!/bin/bash
echo "------------------------------------------------------------"
echo "Aider container is running."
echo "To start aider, exec into this container:"
echo "  docker exec -it <container> aider"
echo "------------------------------------------------------------"

# Keep the container alive
tail -f /dev/null
