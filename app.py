import requests

original_url = "https://nw19.seedr.cc/ff_get/5655602284/www.1TamilMV.day%20-%20Badava%20(2025)%20Tamil%20HQ%20HDRip%20-%20720p%20-%20HEVC%20-%20(DD_5.1%20-%20192Kbps%20_%20AAC%202.0)%20-%20950MB%20-%20ESub.mkv?st=3MyX41U-rEABgMnE16wqqQ&e=1745771591"
forward_url = "https://viber.koyeb.app/ff_get/5655602284/www.1TamilMV.day%20-%20Badava%20(2025)%20Tamil%20HQ%20HDRip%20-%20720p%20-%20HEVC%20-%20(DD_5.1%20-%20192Kbps%20_%20AAC%202.0)%20-%20950MB%20-%20ESub.mkv?st=3MyX41U-rEABgMnE16wqqQ&e=1745771591"

# Forward the URL to another service
response = requests.get(forward_url)
if response.status_code == 200:
    print("Successfully forwarded the URL.")
else:
    print(f"Failed to forward the URL. Status Code: {response.status_code}")
