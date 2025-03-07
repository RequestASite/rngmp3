import logging
from download import download_video

# Enable debugging
logging.basicConfig(level=logging.DEBUG)

# Now, call your function
download_video('https://open.spotify.com/playlist/4kywjeNdgh7Lw3w4m9Q59S?si=0gEx1uFCQci1GhX5kB7tZg', 'static/music')


